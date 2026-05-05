#!/usr/bin/env python3
"""
learn.py — Self-Learning Engine

Structured learning system with ID-based entries, pattern tracking,
priority system, verification loops, and promotion rules.

Usage:
  python3 scripts/learn.py --cycle              # Full learning cycle
  python3 scripts/learn.py --verify             # Check pending verifications
  python3 scripts/learn.py --status             # Show learning stats
  python3 scripts/learn.py --trail              # Dump full learning trail
  python3 scripts/learn.py --log TYPE 'summary' # Log a structured entry
  python3 scripts/learn.py --promote            # Check patterns ready for promotion
"""

import argparse
import json
import os
import glob
import random
import string
from datetime import datetime, timedelta


LEARNING_TRAIL_PATH = os.path.join(
    os.environ.get("OPENCLAW_WORKSPACE", "/home/admin/.openclaw/workspace"),
    "memory",
    ".learning-trail.json",
)
WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", "/home/admin/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
LEARNINGS_DIR = os.path.join(WORKSPACE, ".learnings")


def ensure_trail():
    """Ensure learning trail exists with defaults."""
    default = {
        "version": 2,
        "last_cycle": None,
        "entries": [],       # LRN, ERR, FEAT entries
        "changes": [],       # Applied changes with verification
        "watchlist": [],     # Pattern tracking
        "principles": [],    # Distilled principles
        "stats": {
            "total_entries": 0,
            "total_changes": 0,
            "verified_ok": 0,
            "reverted": 0,
        },
    }
    if not os.path.exists(LEARNING_TRAIL_PATH):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(LEARNING_TRAIL_PATH, "w") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(LEARNING_TRAIL_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        with open(LEARNING_TRAIL_PATH, "w") as f:
            json.dump(default, f, indent=2)
        return default


def save_trail(trail):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(LEARNING_TRAIL_PATH, "w") as f:
        json.dump(trail, f, indent=2)


# ── Memory Management ───────────────────────────────────────────

def auto_daily_log(message, emoji="✅"):
    """Append a log entry to today's memory file."""
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(MEMORY_DIR, f"{today}.md")
    os.makedirs(MEMORY_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%H:%M")
    entry = f"\n### {emoji} {timestamp} - {message}"
    with open(path, "a") as f:
        f.write(entry + "\n")
    return path


def search_memory(query, days=30):
    """Search across memory files for a query."""
    results = []
    cutoff = datetime.now() - timedelta(days=days)
    for f in sorted(glob.glob(os.path.join(MEMORY_DIR, "*.md")), reverse=True):
        if ".dreams" in f:
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(f))
            if mtime < cutoff:
                continue
            with open(f) as fh:
                content = fh.read()
            if query.lower() in content.lower():
                lines = content.split("\n")
                matches = [l.strip() for l in lines if query.lower() in l.lower()][:3]
                results.append({"file": os.path.relpath(f, WORKSPACE), "date": os.path.basename(f).replace(".md", ""), "matches": matches})
        except OSError:
            pass
    return results


def check_memory_retention(trail):
    """Check for expired learning entries (90 days without activity)."""
    now = datetime.now()
    expired = []
    for entry in trail.get("entries", []):
        last_seen = entry.get("last_seen")
        if not last_seen:
            continue
        try:
            days_since = (now - datetime.strptime(last_seen, "%Y-%m-%d")).days
        except ValueError:
            continue
        if days_since > 90 and entry.get("status") == "pending":
            entry["status"] = "wont_fix"
            expired.append((entry.get("id"), entry.get("summary", "")[:40], f"expired ({days_since}d)"))
    if expired:
        save_trail(trail)
    return expired


# ── Detection triggers ──────────────────────────────────────────
    """Generate next ID: LRN-20260505-001, ERR-20260505-A7B, etc."""
    today = datetime.now().strftime("%Y%m%d")
    existing = [
        e["id"] for e in trail.get("entries", [])
        if e["id"].startswith(f"{prefix}-{today}")
    ]
    if existing:
        nums = []
        for eid in existing:
            try:
                nums.append(int(eid.split("-")[-1]))
            except ValueError:
                pass
        if nums:
            next_num = max(nums) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}-{today}-{next_num:03d}"


# ── Log an entry ──────────────────────────────────────────────────

def log_entry(trail, entry_type, summary, area="tooling",
              priority="medium", source="self_discovery",
              pattern_key=None, details="", suggested_action="",
              reproduce_info="", extra_meta=None):
    """Log a structured learning/error/feature entry."""
    today = datetime.now().isoformat()
    date_str = datetime.now().strftime("%Y-%m-%d")

    prefix = {"learning": "LRN", "error": "ERR", "feature": "FEAT",
              "correction": "LRN", "knowledge_gap": "LRN",
              "best_practice": "LRN"}.get(entry_type, "LRN")

    if entry_type in ("correction", "knowledge_gap", "best_practice"):
        entry_type_display = entry_type
        entry_type = "learning"
    else:
        entry_type_display = entry_type

    eid = next_id(trail, prefix)

    entry = {
        "id": eid,
        "type": entry_type,
        "category": entry_type_display if entry_type == "learning" else None,
        "summary": summary[:120],
        "details": details,
        "suggested_action": suggested_action,
        "area": area,
        "priority": priority,
        "status": "pending",
        "logged": today,
        "source": source,
        "pattern_key": pattern_key,
        "recurrence_count": 0,
        "first_seen": date_str,
        "last_seen": date_str,
    }
    if extra_meta:
        entry.update(extra_meta)

    # Check for existing pattern
    if pattern_key:
        for existing in trail.get("entries", []):
            if existing.get("pattern_key") == pattern_key:
                existing["recurrence_count"] = existing.get("recurrence_count", 0) + 1
                existing["last_seen"] = date_str
                existing["status"] = "pending"  # Re-activate
                print(f"🔄 Pattern '{pattern_key}' incremented to {existing['recurrence_count']}x")
                save_trail(trail)
                return existing["id"]

    # New entry
    trail.setdefault("entries", []).append(entry)
    trail["stats"]["total_entries"] = trail["stats"].get("total_entries", 0) + 1
    save_trail(trail)
    print(f"📝 [{eid}] {summary[:60]}")
    return eid


# ── Pattern tracking ─────────────────────────────────────────────

# ── Conflict Detection ──────────────────────────────────────────

CONFLICT_PAIRS = [
    ("headless", "gui"),
    ("read tool", "exec"),
    ("verbose", "concise"),
    ("manual", "automatic"),
    ("complex", "simple"),
]


def detect_conflicts(new_principle, existing_principles):
    """Check if a new principle conflicts with existing ones.
    Returns list of (existing, reason) tuples."""
    conflicts = []
    new_lower = new_principle.lower()

    for existing in existing_principles:
        existing_lower = existing.lower()
        # Check opposite-direction conflict pairs
        for a, b in CONFLICT_PAIRS:
            if (a in new_lower and b in existing_lower) or \
               (b in new_lower and a in existing_lower):
                conflicts.append((existing,
                    f"'{a}' vs '{b}' — opposite directions"))
                break
        # Check direct contradiction (same domain, opposite advice)
        if "don't" in new_lower and "don't" not in existing_lower:
            # Extract what's being negated
            for word in new_lower.replace("don't", "").split():
                if word in existing_lower and len(word) > 3:
                    conflicts.append((existing,
                        f"'{new_principle[:50]}' vs '{existing[:50]}' — direct contradiction"))
                    break

    return conflicts


def assign_priority_score(trail, entry):
    """Calculate numeric priority score for an entry.
    Higher = more important. Used for conflict resolution."""
    score = 0

    # Base priority
    priority_map = {"critical": 100, "high": 60, "medium": 30, "low": 10}
    score += priority_map.get(entry.get("priority", "medium"), 30)

    # Recurrence bonus
    rc = entry.get("recurrence_count", 0)
    score += rc * 10

    # Recency bonus
    last_seen = entry.get("last_seen")
    if last_seen:
        try:
            days_since = (datetime.now() - datetime.strptime(last_seen, "%Y-%m-%d")).days
            score += max(0, 30 - days_since)  # Up to 30 points for freshness
        except ValueError:
            pass

    # Area weight
    area_weights = {
        "security": 50, "behavior": 40, "tooling": 30,
        "config": 20, "tests": 20, "docs": 10,
    }
    score += area_weights.get(entry.get("area", ""), 0)

    return score


# ── Forgetting Mechanism ────────────────────────────────────────

FORGET_DAYS = 30  # Days after which a principle begins to fade


def apply_forgetting(trail):
    """Demote old principles that haven't been reinforced.
    Returns list of demoted principles."""
    now = datetime.now()
    demoted = []

    for entry in trail.get("entries", []):
        last_seen = entry.get("last_seen")
        if not last_seen:
            continue
        try:
            days_since = (now - datetime.strptime(last_seen, "%Y-%m-%d")).days
        except ValueError:
            continue

        # Old, never promoted → auto-resolve
        if days_since > FORGET_DAYS * 2 and entry.get("status") == "pending":
            old_priority = entry.get("priority", "medium")
            entry["priority"] = "low"
            if old_priority != "low":
                demoted.append((entry.get("id", "?"), entry.get("summary", "")[:40],
                              f"{old_priority}→low (unseen {days_since}d)"))

        # Very old, low priority → auto-resolve as wont_fix
        if days_since > FORGET_DAYS * 3 and entry.get("priority") == "low":
            if entry.get("status") == "pending":
                entry["status"] = "wont_fix"
                demoted.append((entry.get("id", "?"), entry.get("summary", "")[:40],
                              "auto-resolved (expired)"))

    # Also check principles array for staleness
    # (principles don't auto-expire, they need manual review)
    stale_principles = []
    for p in trail.get("principles", []):
        # Principles stay until explicitly removed
        pass

    save_trail(trail)
    return demoted


# ── Auto-Revert ─────────────────────────────────────────────────

def auto_revert_failed(trail, max_retries=2):
    """Auto-revert changes that have failed verification multiple times.
    Returns list of reverted change IDs."""
    reverted = []
    now = datetime.now()

    for change in trail.get("changes", []):
        if change.get("verified") or change.get("outcome") == "reverted":
            continue

        nc = change.get("next_check")
        if not nc:
            continue
        try:
            dt = datetime.strptime(nc, "%Y-%m-%d")
        except ValueError:
            continue

        # Overdue by 7+ days and not verified
        days_overdue = (now - dt).days
        if days_overdue < 7:
            continue  # Still within grace period

        check_count = change.get("check_count", 0)
        if check_count >= max_retries:
            # Mark as failed
            change["outcome"] = "auto_reverted"
            change["verified"] = False
            change["evidence"].append(f"Auto-reverted: unchecked for {days_overdue}d past deadline")
            trail["stats"]["reverted"] = trail["stats"].get("reverted", 0) + 1
            reverted.append(change["id"])
            summary = f"⚠️ Change '{change.get('change','')[:50]}' auto-reverted (overdue {days_overdue}d)"
            print(f"   {summary}")
        else:
            # Increment check count, extend deadline
            change["check_count"] = check_count + 1
            extension = (dt + timedelta(days=7)).strftime("%Y-%m-%d")
            change["next_check"] = extension
            change["evidence"].append(f"Extended to {extension} (attempt {check_count+1}/{max_retries})")

    if reverted:
        save_trail(trail)
    return reverted


def find_patterns_ready(trail):
    """Find patterns with Recurrence-Count >= 3 across 2+ sessions."""
    ready = []
    entries = trail.get("entries", [])
    sessions_seen = {}

    for e in entries:
        pk = e.get("pattern_key")
        if not pk:
            continue
        rc = e.get("recurrence_count", 0)
        if pk not in sessions_seen:
            sessions_seen[pk] = {"count": 0, "dates": set()}
        sessions_seen[pk]["count"] = max(sessions_seen[pk]["count"], rc)
        sessions_seen[pk]["dates"].add(e.get("last_seen", ""))

    for pk, data in sessions_seen.items():
        if data["count"] >= 3 and len(data["dates"]) >= 2:
            # Find the entry with this pattern_key
            for e in entries:
                if e.get("pattern_key") == pk:
                    ready.append(e)
                    break
    return ready


def suggest_promotion(entry):
    """Suggest where to promote a recurring pattern."""
    area = entry.get("area", "")
    entry_type = entry.get("type", "")
    category = entry.get("category", "")

    if category == "correction" or area == "behavior":
        return "SOUL.md"
    elif category == "best_practice" or area in ("tooling", "infra"):
        return "TOOLS.md"
    elif area in ("frontend", "backend", "tests", "config"):
        return "AGENTS.md"
    elif entry_type == "error":
        return "TOOLS.md"
    else:
        return "MEMORY.md"


# ── Proposal Generation ─────────────────────────────────────────

def generate_proposals(trail):
    """Generate actionable improvement proposals for user review."""
    proposals = []
    now = datetime.now()

    # 1. Patterns ready for promotion
    ready = find_patterns_ready(trail)
    for entry in ready:
        target = suggest_promotion(entry)
        pk = entry.get("pattern_key", "unknown")
        # Calculate actual recurrence count across all entries with this pattern
        rc = max(e.get("recurrence_count", 0) for e in trail.get("entries", []) if e.get("pattern_key") == pk)
        summary = entry.get("summary", "")
        source = entry.get("source", "")

        # Generate specific change suggestion
        if target == "TOOLS.md":
            change = f"Add to Known Gotchas: '{summary}'"
            risk = "Low — adds a note, doesn't change behavior"
        elif target == "MEMORY.md":
            change = f"Append to Self-Improvement Principles: '{summary}'"
            risk = "Low — adds a principle, doesn't change behavior"
        elif target == "SOUL.md":
            change = f"Add behavioral guideline: '{summary}'"
            risk = "Medium — changes agent persona"
        elif target == "AGENTS.md":
            change = f"Add workflow rule: '{summary}'"
            risk = "Medium — changes agent conventions"
        else:
            change = f"Record: '{summary}'"
            risk = "Low"

        proposals.append({
            "type": "promotion",
            "id": entry.get("id", ""),
            "target": target,
            "change": change,
            "motivation": f"Pattern '{pk}' occurred {rc}x across sessions (source: {source})",
            "risk": risk,
            "effort": "low",
            "impact": "medium" if rc >= 3 else "high",
        })

    # 2. Overdue verifications that need attention
    due, _ = check_verifications(trail)
    for change in due:
        proposals.append({
            "type": "verification",
            "id": change.get("id", ""),
            "target": change.get("target", ""),
            "change": f"Verify: '{change.get('change','')[:60]}'",
            "motivation": f"Hypothesis: {change.get('hypothesis','')} — due since {change.get('next_check','')}",
            "risk": "Low — just checking",
            "effort": "low",
            "impact": "high",
        })

    # 3. High-priority pending items
    for entry in trail.get("entries", []):
        if entry.get("priority") == "critical" and entry.get("status") == "pending":
            proposals.append({
                "type": "critical_fix",
                "id": entry.get("id", ""),
                "target": suggest_promotion(entry),
                "change": f"Address: {entry.get('summary','')[:80]}",
                "motivation": f"Critical priority, {entry.get('recurrence_count',0)}x occurrences",
                "risk": "Medium",
                "effort": "medium",
                "impact": "high",
            })

    return proposals


def print_proposals(proposals):
    """Print proposals in a readable format for user review."""
    if not proposals:
        print("✅ No proposals at this time.")
        return

    print(f"\n📋 {len(proposals)} Proposal(s) for Review:\n")
    for i, p in enumerate(proposals, 1):
        print(f"  [{i}] {p['type'].upper()} → {p['target']}")
        print(f"      Change: {p['change']}")
        print(f"      Why: {p['motivation']}")
        print(f"      Risk: {p['risk']} | Effort: {p['effort']} | Impact: {p['impact']}")
        print()

    print("  To approve: tell me the proposal number")
    print("  To reject: tell me 'skip N'")


# ── Change tracking (for verification) ───────────────────────────

def record_change(trail, target, change, hypothesis,
                  source_entry=None, change_type="file_update"):
    """Record a change with verification tracking."""
    now = datetime.now()
    cid = f"change-{now.strftime('%Y%m%d')}-{trail['stats'].get('total_changes',0)+1:03d}"
    next_check = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    entry = {
        "id": cid,
        "date": now.strftime("%Y-%m-%d"),
        "type": change_type,
        "target": target,
        "change": change[:200],
        "hypothesis": hypothesis[:200],
        "source_entry": source_entry,
        "verified": False,
        "outcome": None,
        "next_check": next_check,
        "check_count": 0,
        "evidence": [],
    }
    trail.setdefault("changes", []).append(entry)
    trail["stats"]["total_changes"] = trail["stats"].get("total_changes", 0) + 1
    save_trail(trail)
    print(f"📌 Change recorded: {cid} → {target} (verify by {next_check})")
    return cid


def check_verifications(trail):
    """Find changes due for verification."""
    now = datetime.now()
    due = []
    pending = []
    for change in trail.get("changes", []):
        if change.get("verified") or change.get("outcome"):
            continue
        nc = change.get("next_check")
        if not nc:
            due.append(change)
        else:
            try:
                dt = datetime.strptime(nc, "%Y-%m-%d")
                if dt <= now:
                    due.append(change)
                else:
                    pending.append(change)
            except ValueError:
                due.append(change)
    return due, pending


# ── Status & reports ─────────────────────────────────────────────

def show_status(trail):
    entries = trail.get("entries", [])
    changes = trail.get("changes", [])
    watchlist = trail.get("watchlist", [])
    principles = trail.get("principles", [])
    stats = trail.get("stats", {})

    print(f"📊 Learning System Status")
    print(f"   Last cycle: {trail.get('last_cycle', 'never')}")
    print(f"   Total entries: {stats.get('total_entries', 0)}")
    print(f"   Changes made: {stats.get('total_changes', 0)}")
    print(f"   Verified OK: {stats.get('verified_ok', 0)}")
    print(f"   Reverted: {stats.get('reverted', 0)}")
    print(f"   Principles: {len(principles)}")

    # Count by priority
    by_priority = {}
    for e in entries:
        p = e.get("priority", "medium")
        by_priority[p] = by_priority.get(p, 0) + 1
    if by_priority:
        print(f"\n📋 Entries by priority:")
        for p in ["critical", "high", "medium", "low"]:
            if p in by_priority:
                print(f"   {p}: {by_priority[p]}")

    # Pending verifications
    due, pend = check_verifications(trail)
    print(f"\n🔍 Verifications: {len(due)} due, {len(pend)} monitoring")

    # Patterns ready for promotion
    ready = find_patterns_ready(trail)
    if ready:
        print(f"\n🚀 Patterns ready for promotion:")
        for r in ready:
            print(f"   • [{r.get('id','?')}] {r.get('summary','')[:60]} → {suggest_promotion(r)}")


def run_full_cycle(trail):
    now = datetime.now()
    trail["last_cycle"] = now.isoformat()
    save_trail(trail)

    print(f"🔄 Learning Cycle — {now.strftime('%Y-%m-%d %H:%M')}\n")

    # Phase 1: Check recent memory
    print(f"📁 Phase 1: Checking recent session data...")
    recent = glob.glob(os.path.join(MEMORY_DIR, "*.md"))
    recent = [f for f in recent if ".dreams" not in f
              and os.path.basename(f) != ".learning-trail.json"]
    print(f"   {len(recent)} memory file(s)")

    # Phase 2: Check verifications
    due, pend = check_verifications(trail)
    print(f"\n✅ Phase 2: Verification check")
    print(f"   {len(due)} due for review, {len(pend)} still monitoring")
    for d in due:
        print(f"   └ [{d.get('id','?')}] {d.get('target','?')}: {d.get('hypothesis','')[:60]}")

    # Phase 3: Check patterns for promotion
    ready = find_patterns_ready(trail)
    print(f"\n🚀 Phase 3: Pattern promotion check")
    if ready:
        for r in ready:
            target = suggest_promotion(r)
            print(f"   └ [{r.get('id','?')}] {r.get('summary','')[:60]} → promote to {target}")
    else:
        print(f"   No patterns ready yet (need ≥3 occurrences across ≥2 sessions)")

    # Phase 4: Forgetting check
    demoted = apply_forgetting(trail)
    print(f"\n⏳ Phase 4: Forgetting check")
    if demoted:
        for eid, summary, detail in demoted:
            print(f"   └ {detail}: [{eid}] {summary}")
    else:
        print(f"   No principles expired (threshold: {FORGET_DAYS}d without reinforcement)")

    # Phase 5: Auto-revert check
    reverted = auto_revert_failed(trail)
    print(f"\n↩️ Phase 5: Auto-revert check")
    if reverted:
        print(f"   Auto-reverted: {len(reverted)} changes")
    else:
        print(f"   No overdue changes to revert")

    # Phase 6: Check for conflicts among principles
    principles = trail.get("principles", [])
    all_conflicts = []
    for i, p in enumerate(principles):
        conflicts = detect_conflicts(p, principles[:i] + principles[i+1:])
        for existing, reason in conflicts:
            all_conflicts.append((p, existing, reason))
    print(f"\n⚡ Phase 6: Conflict check")
    if all_conflicts:
        for new_p, old_p, reason in all_conflicts:
            score_new = assign_priority_score(trail, {"priority": "medium", "recurrence_count": 0, "area": "", "last_seen": None})
            print(f"   ⚠️ {reason}")
            print(f"      '{new_p[:50]}' vs '{old_p[:50]}'")
    else:
        print(f"   No conflicts detected among {len(principles)} principles")

    # Phase 7: Memory retention check
    expired = check_memory_retention(trail)
    print(f"\n🗑️ Phase 7: Memory retention check")
    if expired:
        for eid, summary, detail in expired:
            print(f"   └ {detail}: [{eid}] {summary}")
    else:
        print(f"   No expired entries (threshold: 90d without activity)")

    # Phase 8: Summary
    stats = trail.get("stats", {})
    entries = trail.get("entries", [])
    print(f"\n📊 Phase 8: Summary")
    print(f"   {stats.get('total_entries',0)} total entries")
    print(f"   {stats.get('total_changes',0)} changes, {stats.get('verified_ok',0)} verified, {stats.get('reverted',0)} reverted")
    print(f"   {len(principles)} principles, {len(demoted)} demoted, {len(expired)} expired")

    print(f"\n🤖 Agent follow-up needed:")
    if due:
        print(f"   • Review {len(due)} pending verifications")
    if ready:
        print(f"   • Promote {len(ready)} recurring patterns")
    if all_conflicts:
        print(f"   • Resolve {len(all_conflicts)} conflicting principles")
    if expired:
        print(f"   • {len(expired)} entries expired (auto-resolved)")


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Self-learning engine")
    parser.add_argument("--cycle", action="store_true", help="Full learning cycle")
    parser.add_argument("--verify", action="store_true", help="Check pending verifications")
    parser.add_argument("--status", action="store_true", help="Show learning stats")
    parser.add_argument("--trail", action="store_true", help="Dump full learning trail")
    parser.add_argument("--promote", action="store_true", help="Check patterns ready for promotion")
    parser.add_argument("--log", nargs=2, metavar=("TYPE", "SUMMARY"),
                        help="Log entry: TYPE=learning|error|feature|correction SUMMARY='text'")
    parser.add_argument("--area", default="tooling", help="Area for log entry")
    parser.add_argument("--priority", default="medium",
                        choices=["critical", "high", "medium", "low"])
    parser.add_argument("--pattern-key", default=None, help="Pattern key for dedup")
    parser.add_argument("--add-change", nargs=3, metavar=("TARGET", "CHANGE", "HYPOTHESIS"),
                        help="Record a change with verification")
    parser.add_argument("--add-principle", nargs=1, metavar="PRINCIPLE",
                        help="Add a distilled principle")
    parser.add_argument("--log-daily", nargs=1, metavar="MESSAGE",
                        help="Auto-log to today's memory file")
    parser.add_argument("--search-memory", nargs=1, metavar="QUERY",
                        help="Search across memory files")
    parser.add_argument("--retention", action="store_true",
                        help="Check for expired entries (90d)")
    parser.add_argument("--propose", action="store_true",
                        help="Generate improvement proposals for user review")
    args = parser.parse_args()

    trail = ensure_trail()

    if args.cycle:
        run_full_cycle(trail)
    elif args.verify:
        due, pend = check_verifications(trail)
        print(f"🔍 Verifications: {len(due)} due, {len(pend)} monitoring")
        for d in due:
            print(f"\n  [{d.get('id','?')}] → {d.get('target','?')}")
            print(f"    Change: {d.get('change','')[:80]}")
            print(f"    Hypothesis: {d.get('hypothesis','')[:80]}")
            print(f"    Due: {d.get('next_check','?')}")
    elif args.status:
        show_status(trail)
    elif args.trail:
        print(json.dumps(trail, indent=2))
    elif args.promote:
        ready = find_patterns_ready(trail)
        if ready:
            print(f"🚀 {len(ready)} pattern(s) ready for promotion:")
            for r in ready:
                target = suggest_promotion(r)
                print(f"\n  [{r.get('id','?')}] {r.get('summary','')[:80]}")
                print(f"  → Promote to: {target}")
                print(f"  ↳ Source: {r.get('source','?')}")
        else:
            print("No patterns ready for promotion yet (need ≥3 occurrences across ≥2 sessions)")
    elif args.log:
        etype, summary = args.log
        log_entry(trail, etype, summary,
                  area=args.area, priority=args.priority,
                  pattern_key=args.pattern_key)
    elif args.add_change:
        target, change, hypothesis = args.add_change
        record_change(trail, target, change, hypothesis)
    elif args.add_principle:
        p = args.add_principle[0]
        if p not in trail.get("principles", []):
            trail.setdefault("principles", []).append(p)
            save_trail(trail)
            print(f"💎 Principle added: '{p[:60]}'")
    elif args.log_daily:
        msg = args.log_daily[0]
        path = auto_daily_log(msg)
        print(f"📝 Logged to {os.path.relpath(path, WORKSPACE)}")
    elif args.search_memory:
        query = args.search_memory[0]
        results = search_memory(query)
        if results:
            print(f"🔍 Found {len(results)} file(s) matching '{query}':")
            for r in results:
                print(f"  [{r['date']}] {r['file']}")
                for m in r['matches']:
                    print(f"    → {m[:80]}")
        else:
            print(f"No results for '{query}'")
    elif args.retention:
        expired = check_memory_retention(trail)
        if expired:
            print(f"🗑️ {len(expired)} expired entries resolved:")
            for eid, summary, detail in expired:
                print(f"  [{eid}] {summary} — {detail}")
        else:
            print("✅ No expired entries")
    elif args.propose:
        proposals = generate_proposals(trail)
        print_proposals(proposals)
    else:
        show_status(trail)


if __name__ == "__main__":
    main()
