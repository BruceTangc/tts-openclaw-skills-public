#!/usr/bin/env python3
"""Fail-closed integrity runtime for the A-share AI opportunity trader.

This module does NOT call Eastmoney APIs. It validates locally persisted
Opportunity/Decision/Execution state before a mutating mx-moni request may be
sent, and maintains a durable intent ledger for idempotency/reconciliation.

The caller remains responsible for invoking the installed mx-moni skill with a
natural-language query after authorize() returns ALLOW.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOW_RESULTS = {"ALLOW", "REDUCE_SIZE"}
TERMINAL_INTENT_STATES = {"FILLED", "REJECTED", "RECONCILED"}
BLOCKING_INTENT_STATES = {"CREATED", "AUTHORIZED", "SUBMITTED", "PARTIAL", "UNKNOWN"}
MUTATING_TERMS = (
    "买入", "买进", "建仓", "加仓", "卖出", "抛售", "减仓", "清仓",
    "buy", "sell", "add", "reduce", "exit",
)
READ_ONLY_TERMS = (
    "查询", "查看", "持仓", "资金", "余额", "委托", "订单", "成交", "历史",
    "query", "list", "show", "position", "cash", "balance", "order", "fill", "history",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ledger_path(root: Path) -> Path:
    return root / "state" / "runtime" / "trade-intents.json"


def audit_path(root: Path) -> Path:
    return root / "state" / "runtime" / "authorization-audit.jsonl"


def load_ledger(root: Path) -> dict[str, Any]:
    path = ledger_path(root)
    if not path.exists():
        return {"schema_version": 1, "intents": {}}
    data = load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("intents"), dict):
        raise RuntimeError("INTENT_LEDGER_CORRUPT")
    return data


def save_ledger(root: Path, ledger: dict[str, Any]) -> None:
    atomic_write_json(ledger_path(root), ledger)
    # Read-back verification is part of the commit contract.
    check = load_json(ledger_path(root))
    if check != ledger:
        raise RuntimeError("INTENT_LEDGER_VERIFY_FAILED")


def append_audit(root: Path, event: dict[str, Any]) -> None:
    path = audit_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def fingerprint(intent: dict[str, Any]) -> str:
    canonical = {
        "opportunity_id": intent.get("opportunity_id"),
        "decision_id": intent.get("decision_id"),
        "action": str(intent.get("action", "")).upper(),
        "symbol": str(intent.get("symbol", "")),
        "quantity": intent.get("quantity"),
        "price_policy": intent.get("price_policy"),
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify_mx_moni_query(query: str) -> str:
    q = query.strip().lower()
    if any(term.lower() in q for term in MUTATING_TERMS):
        return "CAPITAL_MUTATION"
    if any(term.lower() in q for term in READ_ONLY_TERMS):
        return "READ_ONLY"
    # Unknown intent is never allowed to reach a capital tool implicitly.
    return "UNKNOWN"


def _find_json_record(directory: Path, record_id: str) -> dict[str, Any] | None:
    if not directory.exists():
        return None
    for p in directory.rglob("*.json"):
        try:
            data = load_json(p)
        except Exception:
            continue
        if isinstance(data, dict) and record_id in {
            str(data.get("opportunity_id", "")), str(data.get("decision_id", ""))
        }:
            return data
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and record_id in {
                    str(item.get("opportunity_id", "")), str(item.get("decision_id", ""))
                }:
                    return item
    return None


def authorize(root: Path, intent: dict[str, Any]) -> dict[str, Any]:
    required = ["trade_intent_id", "opportunity_id", "decision_id", "action", "symbol", "quantity"]
    missing = [k for k in required if intent.get(k) in (None, "")]
    reasons: list[str] = []
    if missing:
        reasons.append("MISSING_FIELDS:" + ",".join(missing))

    tid = str(intent.get("trade_intent_id", ""))
    action = str(intent.get("action", "")).upper()
    opp = _find_json_record(root / "state" / "opportunities", str(intent.get("opportunity_id", "")))
    dec = _find_json_record(root / "state" / "decisions", str(intent.get("decision_id", "")))

    if opp is None:
        reasons.append("OPPORTUNITY_NOT_FOUND")
    else:
        stage = str(opp.get("stage", "")).upper()
        lifecycle = str((opp.get("hypothesis") or {}).get("lifecycle", "")).upper()
        if stage == "CLOSED" or lifecycle == "INVALIDATED":
            reasons.append("OPPORTUNITY_CLOSED_OR_INVALIDATED")

    if dec is None:
        reasons.append("DECISION_NOT_FOUND")
    else:
        if not bool(dec.get("persisted", False)):
            reasons.append("DECISION_NOT_VERIFIED_PERSISTED")
        if str(dec.get("result", "")).upper() not in ALLOW_RESULTS:
            reasons.append("DECISION_RESULT_NOT_AUTHORIZED")
        if str(dec.get("action", "")).upper() != action:
            reasons.append("ACTION_MISMATCH")
        if dec.get("trade_intent_id") not in (None, "", tid):
            reasons.append("TRADE_INTENT_MISMATCH")
        if dec.get("symbol") not in (None, "", intent.get("symbol")):
            reasons.append("SYMBOL_MISMATCH")
        max_qty = dec.get("max_quantity", dec.get("quantity"))
        if max_qty is not None:
            try:
                if int(intent.get("quantity", 0)) > int(max_qty):
                    reasons.append("QUANTITY_EXCEEDS_AUTHORIZATION")
            except Exception:
                reasons.append("INVALID_QUANTITY")
        for flag in ("portfolio_refreshed", "t_plus_1_passed", "liquidity_passed", "risk_passed"):
            if dec.get(flag) is not True:
                reasons.append(flag.upper() + "_REQUIRED")

    ledger = load_ledger(root)
    intents = ledger["intents"]
    fp = fingerprint(intent)
    if tid in intents:
        reasons.append("DUPLICATE_TRADE_INTENT_ID")
    for old_id, old in intents.items():
        if old.get("fingerprint") == fp and old.get("state") in BLOCKING_INTENT_STATES:
            reasons.append("EQUIVALENT_INTENT_ALREADY_ACTIVE:" + old_id)
            break

    unresolved = [
        iid for iid, rec in intents.items()
        if rec.get("state") == "UNKNOWN" and rec.get("symbol") == intent.get("symbol")
    ]
    if unresolved:
        reasons.append("UNRESOLVED_EXECUTION:" + ",".join(unresolved))

    result = "BLOCK" if reasons else "ALLOW"
    event = {
        "at": now_iso(), "type": "EXECUTION_AUTHORIZATION", "result": result,
        "trade_intent_id": tid, "opportunity_id": intent.get("opportunity_id"),
        "decision_id": intent.get("decision_id"), "action": action,
        "symbol": intent.get("symbol"), "quantity": intent.get("quantity"), "reasons": reasons,
    }
    append_audit(root, event)
    if reasons:
        return event

    intents[tid] = {
        **intent, "fingerprint": fp, "state": "AUTHORIZED", "authorized_at": event["at"]
    }
    save_ledger(root, ledger)
    return event


def update_intent(root: Path, tid: str, state: str, details: dict[str, Any]) -> dict[str, Any]:
    allowed = {"SUBMITTED", "PARTIAL", "FILLED", "REJECTED", "UNKNOWN", "RECONCILED"}
    state = state.upper()
    if state not in allowed:
        raise RuntimeError("INVALID_INTENT_STATE")
    ledger = load_ledger(root)
    rec = ledger["intents"].get(tid)
    if rec is None:
        raise RuntimeError("TRADE_INTENT_NOT_FOUND")
    old = rec.get("state")
    if old in TERMINAL_INTENT_STATES and state != "RECONCILED":
        raise RuntimeError("TERMINAL_INTENT_CANNOT_REOPEN")
    rec.update(details)
    rec["state"] = state
    rec["updated_at"] = now_iso()
    if state == "UNKNOWN":
        rec["reconciliation_required"] = True
    if state == "RECONCILED":
        if not details.get("verified_by_mx_moni"):
            raise RuntimeError("RECONCILIATION_REQUIRES_MX_MONI_EVIDENCE")
        rec["reconciliation_required"] = False
    save_ledger(root, ledger)
    append_audit(root, {"at": rec["updated_at"], "type": "INTENT_STATE", "trade_intent_id": tid, "from": old, "to": state})
    return rec


def verify_first_seen(root: Path, discovery_file: Path) -> dict[str, Any]:
    data = load_json(discovery_file)
    did = str(data.get("discovery_id", ""))
    first_seen = str(data.get("first_seen", ""))
    if not did or not first_seen:
        return {"result": "BLOCK", "reason": "DISCOVERY_ID_OR_FIRST_SEEN_MISSING"}
    anchor_dir = root / "state" / "runtime" / "discovery-anchors"
    anchor = anchor_dir / (re.sub(r"[^A-Za-z0-9_.-]", "_", did) + ".json")
    canonical = {"discovery_id": did, "first_seen": first_seen}
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    if not anchor.exists():
        record = {**canonical, "sha256": digest, "anchored_at": now_iso()}
        atomic_write_json(anchor, record)
        return {"result": "ANCHORED", **record}
    old = load_json(anchor)
    if old.get("first_seen") != first_seen or old.get("sha256") != digest:
        return {"result": "BLOCK", "reason": "FIRST_SEEN_INTEGRITY_VIOLATION", "anchor": old, "current": canonical}
    return {"result": "PASS", "discovery_id": did, "first_seen": first_seen, "sha256": digest}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify"); c.add_argument("query")
    a = sub.add_parser("authorize"); a.add_argument("intent_json")
    u = sub.add_parser("update-intent"); u.add_argument("trade_intent_id"); u.add_argument("state"); u.add_argument("details_json", nargs="?", default="{}")
    v = sub.add_parser("verify-first-seen"); v.add_argument("discovery_file")
    args = p.parse_args()
    root = Path(args.root).resolve()
    try:
        if args.cmd == "classify":
            out = {"classification": classify_mx_moni_query(args.query)}
        elif args.cmd == "authorize":
            out = authorize(root, json.loads(args.intent_json))
        elif args.cmd == "update-intent":
            out = update_intent(root, args.trade_intent_id, args.state, json.loads(args.details_json))
        else:
            out = verify_first_seen(root, Path(args.discovery_file).resolve())
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if out.get("result") not in {"BLOCK"} else 2
    except Exception as e:
        print(json.dumps({"result": "BLOCK", "reason": type(e).__name__, "detail": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
