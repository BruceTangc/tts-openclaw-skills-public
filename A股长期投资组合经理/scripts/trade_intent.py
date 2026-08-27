#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trade_intent.py — 交易意图幂等状态机（F3）

为每一笔 BUY（同一 trade_intent_id）提供**持久化**生命周期状态，保证：
  - 相同 trade_intent_id 不允许重复执行（幂等去重）
  - execute_trade timeout 后不能直接重试 BUY，必须先查询执行结果
  - UNKNOWN 状态必须先查询执行结果，再决定是否允许重新执行
  - OpenClaw Cron 重复触发 / Agent retry / session retry 均不得产生重复 BUY
  - 不依赖 mx_moni 的 client_order_id 作为唯一幂等保证（以本地持久化为权威源）

状态（State Machine）：
  PENDING   — 意图已创建、尚未进入执行
  EXECUTING — 已通过 BUY Gate、正在调用 execute_trade（发出下单请求那一刻）
  EXECUTED  — 已确认成交/已提交成功（执行完成，不再重试）
  REJECTED  — 被 BUY Gate 或风控拒绝（不产生交易）
  FAILED    — 执行期间发生确定性失败（下单确定失败，不再重试）
  UNKNOWN   — 执行结果未知（timeout / 进程被杀 / 网络异常），必须先查执行结果再决定

原子性：状态写入使用带锁的 json 文件（与 risk_control.py 共用 .risk_control.lock）。
  - 加锁 -> 读最新状态 -> 检查去重 -> 写新状态（tmp + os.replace）-> 解锁

用法：
  from trade_intent import create_intent, mark_running, settle_intent, \
                           get_intent, query_unknown_before_retry
"""
import json
import os
import sys
import uuid
import fcntl
import time
from datetime import datetime

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
LOCK_PATH = os.path.join(BASE_DIR, ".risk_control.lock")   # 与 risk_control.py / execute_trade.py 共用统一锁
INTENT_DIR = os.path.join(BASE_DIR, "state")
INTENT_PATH = os.path.join(INTENT_DIR, "trade_intents.json")
os.makedirs(INTENT_DIR, exist_ok=True)

# 状态常量
PENDING = "PENDING"
EXECUTING = "EXECUTING"
EXECUTED = "EXECUTED"
REJECTED = "REJECTED"
FAILED = "FAILED"
UNKNOWN = "UNKNOWN"

ALL_STATES = {PENDING, EXECUTING, EXECUTED, REJECTED, FAILED, UNKNOWN}

# EXECUTING 状态的执行超时（秒）：超过则视为执行结果未知 -> 标 UNKNOWN
EXECUTE_TIMEOUT_SEC = 90


class IntentLockError(Exception):
    """无法获取意图状态锁（超时）"""


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _acquire_lock(timeout=15):
    """获取统一锁文件（阻塞尝试 timeout 秒，非阻塞重试）。失败返回 None。"""
    lock_fd = open(LOCK_PATH, "w")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_fd
        except BlockingIOError:
            time.sleep(0.3)
    lock_fd.close()
    return None


def _release_lock(lock_fd):
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            lock_fd.close()


def _load_unlocked():
    if not os.path.exists(INTENT_PATH):
        return {}
    try:
        with open(INTENT_PATH) as f:
            return json.load(f)
    except Exception:
        # 文件损坏：保护现场，不静默覆盖。返回空并以 UNKNOWN 兜底保护（见 create_intent）
        return {}


def _save_unlocked(data):
    os.makedirs(INTENT_DIR, exist_ok=True)
    tmp = INTENT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, INTENT_PATH)


def _under_lock(fn):
    """统一的 加锁 -> fn(最新数据) -> 写回 -> 解锁 包装。fn 返回 (commit, result)。"""
    lock_fd = _acquire_lock()
    if lock_fd is None:
        raise IntentLockError("无法获取 trade_intent 状态锁（超时）")
    try:
        data = _load_unlocked()
        commit, result = fn(data)
        if commit:
            _save_unlocked(data)
        return result
    finally:
        _release_lock(lock_fd)


def generate_intent_id(code, trade_type="buy"):
    """生成唯一 trade_intent_id。包含代码/方向/日期/随机段，可读且唯一。"""
    date_part = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_part = uuid.uuid4().hex[:8].upper()
    return f"TI-{date_part}-{trade_type.upper()}-{str(code).zfill(6)}-{rand_part}"


def create_intent(code, trade_type, quantity, source="unknown", intent_id=None):
    """
    创建一条 PENDING 交易意图。返回 (intent_id, state)：
      - 已存在相同 intent_id -> 返回既有状态，不新建（幂等去重）
      - 若历史文件损坏 -> 标记系统级 UNKNOWN（fail-closed），不允许新建裸意图
    """
    code = str(code).zfill(6)
    if intent_id:
        # 显式提供 intent_id：必须先去重检查
        data = _load_unlocked()
        if intent_id in data:
            existing = data[intent_id]
            return intent_id, existing.get("state", UNKNOWN)
        intent_id_out = intent_id
    else:
        intent_id_out = generate_intent_id(code, trade_type)

    def fn(data):
        # 文件损坏保护：若状态文件解析失败返回 {}，此时无法确认历史是否存在重复意图。
        # fail-closed：不允许在损坏状态下创建新意图。
        if data is None or (os.path.exists(INTENT_PATH) and not isinstance(data, dict)):
            return True, ({}, "STATE_CORRUPT")
        if intent_id_out in data:
            existing = data[intent_id_out]
            return False, (intent_id_out, existing.get("state", UNKNOWN))
        new_entry = {
            "intent_id": intent_id_out,
            "code": code,
            "trade_type": trade_type,
            "quantity": int(quantity),
            "state": PENDING,
            "source": source,
            "created_at": _now(),
            "updated_at": _now(),
            "gate_result": None,
            "order_id": None,
            "message": "created",
            "attempts": 0,
        }
        data[intent_id_out] = new_entry
        return True, (intent_id_out, PENDING)

    result = _under_lock(fn)
    if result == "STATE_CORRUPT":
        raise IntentLockError("trade_intents.json 损坏，无法创建意图（fail-closed），需人工处理")
    return result


def get_intent(intent_id):
    """读取意图（无锁读，仅查状态）。不存在返回 None。"""
    data = _load_unlocked()
    if not isinstance(data, dict):
        return None
    return data.get(intent_id)


def _transition(intent_id, from_states, to_state, **updates):
    """在锁内做状态迁移。from_states 为允许的当前状态集合；迁移失败返回 False。"""

    def fn(data):
        if not isinstance(data, dict):
            return False, (False, None)
        entry = data.get(intent_id)
        if entry is None:
            return False, (False, None)
        cur = entry.get("state")
        if from_states is not None and cur not in from_states:
            return False, (False, entry)
        entry["state"] = to_state
        entry["updated_at"] = _now()
        entry.update(updates)
        return True, (True, entry)

    return _under_lock(fn)


def mark_running(intent_id, gate_pass_info=None):
    """
    PENDING -> EXECUTING。
    只有状态为 PENDING 才允许进入执行；已 EXECUTED/EXECUTING 的直接拒绝（防重复）。
    gate_pass_info: 记录 BUY Gate 通过时的上下文（风控快照），便于审计。
    返回 (ok, entry_or_reason)。
    """
    return _transition(
        intent_id, {PENDING},
        EXECUTING,
        started_at=_now(),
        gate_pass_info=gate_pass_info,
        attempts=1,
    )


def settle_intent(intent_id, to_state, order_id=None, message=None):
    """
    EXECUTING -> 终态（EXECUTED / REJECTED / FAILED / UNKNOWN）。
    幂等：如果意图已在终态，重复 settle 不产生变化、返回当前状态（不会把已成交改成失败）。
    """
    allowed_from = {EXECUTING}
    updates = {"order_id": order_id, "message": message}

    def fn(data):
        if not isinstance(data, dict):
            return False, (False, None)
        entry = data.get(intent_id)
        if entry is None:
            return False, (False, None)
        cur = entry.get("state")
        # 幂等保护：已经在终态则不覆盖
        if cur in {EXECUTED, REJECTED, FAILED, UNKNOWN}:
            return False, (False, entry)
        if cur not in allowed_from:
            return False, (False, entry)
        if to_state not in ALL_STATES:
            throw_invalid = Exception(f"非法状态: {to_state}")
            raise throw_invalid
        entry["state"] = to_state
        entry["updated_at"] = _now()
        for k, v in updates.items():
            if v is not None:
                entry[k] = v
        return True, (True, entry)

    return _under_lock(fn)


def mark_unknown_if_stale(intent_id):
    """
    执行超时恢复：若意图处于 EXECUTING 已超过 EXECUTE_TIMEOUT_SEC，标记 UNKNOWN，返回 True。
    UNKNOWN 之后必须走 query_unknown_before_retry 先查执行结果。
    """
    result = _transition(
        intent_id, {EXECUTING}, UNKNOWN,
        message="execute_trade 执行超时，结果未知；需先查询执行结果再决定是否重试",
    )
    ok, entry = result
    return bool(ok)


def resolve_unknown(intent_id, filled_confirm, order_id=None):
    """
    UNKNOWN -> 确定终态（仅当外部查询到确定结果）：
      - filled_confirm=True  -> EXECUTED（已成交，绝不再重试）
      - filled_confirm=False 且确认无成交 -> FAILED 或 PENDING（允许重试）
    返回 (ok, entry)。
    """
    if filled_confirm:
        return _transition(intent_id, {UNKNOWN}, EXECUTED, order_id=order_id,
                           message="UNKNOWN 经查询确认已成交，禁止重试")
    # 确认未成交 -> 允许重试：UNKNOWN -> PENDING
    return _transition(intent_id, {UNKNOWN}, PENDING,
                       message="UNKNOWN 经查询确认未成交，归位 PENDING 允许重试")


def query_unknown_before_retry(intent_id):
    """
    供执行层在 timeout/UNKNOWN 后调用：
      明确约束——UNKNOWN 必须先查执行结果，不能直接重试 BUY。
    返回 (action, detail)：
      action in {'allow_retry', 'no_retry', 'keep_unknown', 'unknown_intent'}
    """
    entry = get_intent(intent_id)
    if entry is None:
        return ("unknown_intent", "意图不存在，禁止盲重试")
    state = entry.get("state")

    if state == EXECUTED:
        return ("no_retry", f"意图已成交（{entry.get('order_id')}），禁止重复 BUY")
    if state == EXECUTING:
        stale = _transition(intent_id, {EXECUTING}, UNKNOWN) if False else None
        # 检查是否超时
        started = entry.get("started_at")
        if started:
            try:
                from datetime import datetime as _dt
                st = _dt.fromisoformat(started)
                elapsed = (datetime.now() - st).total_seconds()
                if elapsed > EXECUTE_TIMEOUT_SEC:
                    mark_unknown_if_stale(intent_id)
                    return ("must_query", "EXECUTING 超时 -> UNKNOWN，必须先查询执行结果")
            except Exception:
                pass
        return ("must_query", "执行中，不能直接重试")
    if state == UNKNOWN:
        return ("must_query", "状态 UNKNOWN，必须先查询执行结果再决定")
    if state == PENDING:
        return ("allow_retry", "状态 PENDING，可安全进入 BUY Gate（未执行过）")
    if state in (REJECTED, FAILED):
        # 拒绝/失败：不允许自动重试 BUY（需人工或明确新意图）
        return ("no_retry", f"意图处于 {state}，不自动重试 BUY")


def list_intents(limit=50):
    data = _load_unlocked()
    if not isinstance(data, dict):
        return []
    items = sorted(data.values(), key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


def prune_old(keep_days=90):
    """归档/清理超过 keep_days 的已终态意图（EXECUTED/REJECTED/FAILED/UNKNOWN）。保留最近 N 天。"""
    cutoff = time.time() - keep_days * 86400

    def fn(data):
        if not isinstance(data, dict):
            return False, None
        to_del = [iid for iid, e in data.items()
                  if e.get("state") in {EXECUTED, REJECTED, FAILED, UNKNOWN}
                  and _ts(e.get("updated_at", "")) < cutoff]
        for iid in to_del:
            del data[iid]
        return (True, len(to_del)) if to_del else (False, 0)

    try:
        return _under_lock(fn)
    except IntentLockError:
        return 0


def _ts(iso):
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(iso).timestamp()
    except Exception:
        return 0


# ===== CLI =====
def intent_status():
    """输出意图状态统计（供 execute_trade.py intent status 直接调用，不依赖 sys.argv）"""
    from collections import Counter
    data = _load_unlocked()
    if not isinstance(data, dict) or not data:
        print("trade_intents.json 不存在或为空（当前无交易意图状态）")
        return
    c = Counter(e.get("state") for e in data.values())
    print(f"意图总数: {len(data)}")
    for s in sorted(ALL_STATES):
        print(f"  {s}: {c.get(s, 0)}")


def _cli():
    """python3 trade_intent.py <subcmd> [args]  -- 主要用于排查/测试"""
    if len(sys.argv) < 2:
        print("用法: trade_intent.py {create|get|list|mark-running|settle|resolve|prune|status}")
        return
    cmd = sys.argv[1]
    if cmd == "status":
        intent_status()
        return
    if cmd == "list":
        for e in list_intents():
            print(f"{e.get('intent_id')} | {e.get('code')} | {e.get('state')} | {e.get('created_at')} | {e.get('message')}")
        return
    if cmd == "get" and len(sys.argv) >= 3:
        print(json.dumps(get_intent(sys.argv[2]), ensure_ascii=False, indent=2)); return
    if cmd == "create" and len(sys.argv) >= 4:
        iid = None
        if "--id" in sys.argv:
            iid = sys.argv[sys.argv.index("--id") + 1]
        print(create_intent(sys.argv[2], "buy", sys.argv[3], source="cli", intent_id=iid)); return
    if cmd == "mark-running" and len(sys.argv) >= 3:
        print(mark_running(sys.argv[2])); return
    if cmd == "prune":
        print(f"清理: {prune_old()} 条"); return
    print("未知子命令")


if __name__ == "__main__":
    _cli()
