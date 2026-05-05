#!/usr/bin/env python3
"""
reflect.py — Detection & Auto-Log for Self-Learning

Detects learning opportunities (corrections, errors, feature requests)
and auto-logs structured entries. Run at session end or on demand.

Usage:
  python3 scripts/reflect.py --collect recent    # Collect session data
  python3 scripts/reflect.py --log "summary"     # Quick auto-log with detection
  python3 scripts/reflect.py --detect "TEXT"     # Analyze text for triggers
"""

import argparse
import json
import os
import glob
from datetime import datetime, timedelta
import re

WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", "/home/admin/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
LEARNING_TRAIL_PATH = os.path.join(MEMORY_DIR, ".learning-trail.json")


# ── Detection triggers ──────────────────────────────────────────

CORRECTION_PATTERNS = [
    r"(?:no|not|wrong|incorrect|actually|mistake|error|that['']s not)",
    r"(?:should (?:be|use|have|do))",
    r"(?:don['']t|doesn['']t|isn['']t|aren['']t|wasn['']t)",
    r"(?:you['']re wrong|you made a mistake|that['']s wrong)",
    r"(?:let me correct|could you fix|fix this|wrong answer)",
]

FEATURE_PATTERNS = [
    r"(?:can you (?:also|add|make|do|create))",
    r"(?:i wish|i need|i want|i would like|it would be great)",
    r"(?:is there a way|could you also|why can['']t)",
    r"(?:feature request|new feature|missing feature)",
]

ERROR_PATTERNS = [
    r"(?:failed|error|exception|traceback|timeout|crash)",
    r"(?:exit code|non-zero|unexpected output)",
    r"(?:connection refused|not found|permission denied)",
    r"(?:syntax error|typeerror|attributeerror|keyerror|importerror)",
]

KNOWLEDGE_GAP_PATTERNS = [
    r"(?:actually, it works like this|the correct way is)",
    r"(?:i didn['']t know|you need to understand)",
    r"(?:let me explain|what you don['']t know)",
    r"(?:that['']s outdated|no longer works|deprecated)",
]


def detect_triggers(text):
    """Analyze text for learning triggers."""
    results = []
    text_lower = text.lower()

    # Corrections
    for pat in CORRECTION_PATTERNS:
        if re.search(pat, text_lower):
            results.append(("correction", text[:80]))
            break

    # Feature requests
    for pat in FEATURE_PATTERNS:
        if re.search(pat, text_lower):
            results.append(("feature", text[:80]))
            break

    # Errors
    for pat in ERROR_PATTERNS:
        if re.search(pat, text_lower):
            results.append(("error", text[:80]))
            break

    # Knowledge gaps
    for pat in KNOWLEDGE_GAP_PATTERNS:
        if re.search(pat, text_lower):
            results.append(("knowledge_gap", text[:80]))
            break

    return results


# ── Collection ──────────────────────────────────────────────────

def find_recent_memory(hours=48):
    now = datetime.now()
    since = now - timedelta(hours=hours)
    files = []
    for f in sorted(glob.glob(os.path.join(MEMORY_DIR, "*.md"))):
        if ".dreams" in f:
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(f))
            if mtime >= since:
                with open(f) as fh:
                    content = fh.read()
                files.append({
                    "path": os.path.relpath(f, WORKSPACE),
                    "mtime": mtime.isoformat(),
                    "size": len(content),
                })
        except OSError:
            pass
    return files


# ── Auto-log to memory ─────────────────────────────────────────

def auto_log_today(task, outcome="success", error=""):
    """Append a task entry to today's memory file."""
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(MEMORY_DIR, f"{today}.md")
    os.makedirs(MEMORY_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%H:%M")
    emoji = "✅" if outcome == "success" else "❌"
    entry = f"\n### {emoji} {timestamp} - {task}"
    if error:
        entry += f"\n   Error: {error}"

    with open(path, "a") as f:
        f.write(entry + "\n")
    print(f"📝 Logged to {os.path.relpath(path, WORKSPACE)}")
    return entry


# ── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Detection & auto-log for self-learning")
    parser.add_argument("--collect", nargs="?", const="recent",
                        choices=["recent", "failed", "all"],
                        help="Collect session data")
    parser.add_argument("--hours", type=int, default=48, help="Lookback hours")
    parser.add_argument("--log", nargs="+", help="'task description' [success|failure] [error]")
    parser.add_argument("--detect", nargs=1, metavar="TEXT",
                        help="Analyze text for learning triggers")
    args = parser.parse_args()

    if args.detect:
        text = args.detect[0]
        triggers = detect_triggers(text)
        if triggers:
            print(f"🔍 Detected triggers in text:")
            for t, snippet in triggers:
                print(f"   • {t}: \"{snippet}...\"")
        else:
            print("No triggers detected")
        return

    if args.log:
        task = args.log[0]
        outcome = args.log[1] if len(args.log) > 1 else "success"
        error = " ".join(args.log[2:]) if len(args.log) > 2 else ""
        auto_log_today(task, outcome, error)
        return

    if args.collect:
        files = find_recent_memory(args.hours)
        print(f"📁 Collected {len(files)} memory files ({args.hours}h)")
        for f in files[:5]:
            print(f"   • {f['path']}")
        if len(files) > 5:
            print(f"   ... and {len(files)-5} more")
        print(f"\n🔍 Suggested checks:")
        print(f"   • Any corrections from user?")
        print(f"   • Any tool errors?")
        print(f"   • Any feature requests?")
        print(f"   • Any new patterns detected?")
        return

    print("Usage:")
    print("  --collect [recent]     Collect session data")
    print("  --log TASK [outcome]   Auto-log to today's memory")
    print("  --detect 'TEXT'        Analyze text for triggers")


if __name__ == "__main__":
    main()
