#!/usr/bin/env python3
"""
选股结果主板过滤脚本。
读取 mx-xuangu 输出的 CSV/raw JSON，过滤出仅沪市主板(60)和深市主板(00)股票。
创业板(30)、科创板(688)、北交所(8)直接剔除。

用法：
  python3 filter_main_board.py <选股CSV或JSON文件路径>
  python3 filter_main_board.py --latest          # 自动找最新的 xuangu CSV
  python3 filter_main_board.py --file <路径>      # 显式指定文件（推荐，避免恢复时抓错）

输出：
  - stdout: 过滤后的股票列表（代码 名称）
  - 退出码 0 正常，退出码 1 无结果
"""
import csv, json, os, sys, re, glob

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
OUTPUT_DIR = os.path.join(BASE_DIR, "tmp/mx_data_output")

CODE_PATTERN = re.compile(r'^(60|00)\d{4}$')


def find_latest_xuangu():
    """查找最新的 xuangu CSV 文件"""
    pattern = os.path.join(OUTPUT_DIR, "mx_xuangu_*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def extract_code_and_name(row, headers):
    """从 CSV 行中提取股票代码和名称。优先匹配「代码」列，避免被 CHOICE_INNER_CODE 等干扰。"""
    code = name = None
    # 第一遍：精确找「代码」或「sec_code」
    for i, h in enumerate(headers):
        hl = h.strip()
        if i < len(row):
            if hl == '代码' or hl == 'sec_code' or hl == 'secCode':
                code = str(row[i]).strip().zfill(6)
            elif hl == '名称' or hl == 'sec_name' or hl == 'secName':
                name = str(row[i]).strip()
    # 第二遍：兜底用包含 code 的列（但不覆盖已找到的）
    if not code:
        for i, h in enumerate(headers):
            hl = h.lower().strip()
            if i < len(row) and ('code' in hl or '代码' in hl):
                val = str(row[i]).strip().zfill(6)
                if re.match(r'^(60|00|30|68|8)\d{4,5}$', val):
                    code = val
                    break
    return code, name


def filter_csv(path):
    """过滤 CSV 文件"""
    results = []
    rejected = []
    try:
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return results, rejected
        headers = rows[0]
        for row in rows[1:]:
            code, name = extract_code_and_name(row, headers)
            if not code:
                continue
            if CODE_PATTERN.match(code):
                results.append((code, name or ''))
            else:
                rejected.append((code, name or ''))
    except Exception as e:
        print(f"❌ CSV 解析失败: {e}", file=sys.stderr)
        return results, rejected
    return results, rejected


def filter_json(path):
    """过滤 mx-xuangu 返回的 raw JSON"""
    results = []
    rejected = []
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
        return results, rejected

    # mx-xuangu 返回格式可能是 data.list / data / data.data.allResults.result.dataList
    # 优先解析真实数据字段：data.data.allResults.result.dataList（mx-xuangu 当前实际结构）
    items = []
    d = data.get('data', data)
    if isinstance(d, dict):
        # 结构1：data.data.allResults.result.dataList（嵌套两层 data）
        try:
            inner = d.get('data') if isinstance(d.get('data'), dict) else d
            all_res = inner.get('allResults') or {}
            result = all_res.get('result') or {}
            items = result.get('dataList', []) or []
        except Exception:
            items = []
        if not items:
            # 结构2：data.list / data.results / data.records
            items = d.get('list', d.get('results', d.get('records', [])))
    elif isinstance(d, list):
        items = d

    for item in items:
        code = str(item.get('SECURITY_CODE', item.get('secCode', item.get('code', item.get('ts_code', ''))))).strip().zfill(6)
        name = item.get('SECURITY_SHORT_NAME', item.get('secName', item.get('name', item.get('stock_name', ''))))
        if not code or code == '000000':
            continue
        if CODE_PATTERN.match(code):
            results.append((code, name))
        else:
            rejected.append((code, name))
    return results, rejected


def main():
    path = None
    if '--latest' in sys.argv:
        path = find_latest_xuangu()
        if not path:
            print("❌ 未找到 xuangu CSV 文件")
            sys.exit(2)
    elif '--file' in sys.argv:
        idx = sys.argv.index('--file')
        if idx + 1 < len(sys.argv):
            path = sys.argv[idx + 1]
        else:
            print("❌ --file 需要指定文件路径")
            sys.exit(2)
    elif len(sys.argv) > 1:
        path = sys.argv[1]

    if not path or not os.path.exists(path):
        print(f"❌ 文件不存在: {path or '(未指定)'}")
        print("用法: python3 filter_main_board.py <xuangu_csv_or_json>")
        print("      python3 filter_main_board.py --latest")
        sys.exit(2)

    print(f"📂 源文件: {os.path.basename(path)}")

    if path.endswith('.json'):
        results, rejected = filter_json(path)
    else:
        results, rejected = filter_csv(path)

    print(f"📊 原始候选: {len(results) + len(rejected)} 只")
    print(f"✅ 主板通过: {len(results)} 只")
    print(f"🚫 被淘汰(非主板): {len(rejected)} 只")

    if rejected:
        for code, name in rejected:
            print(f"   🚫 {code} {name}")

    if not results:
        print("⚠️ 无主板候选通过 — 本次选股无合格标的")
        sys.exit(1)

    print()
    print("=" * 50)
    print("✅ 主板候选列表（传给 LLM 做基本面验证）：")
    for code, name in results:
        print(f"   {code}  {name}")

    sys.exit(0)


if __name__ == '__main__':
    main()
