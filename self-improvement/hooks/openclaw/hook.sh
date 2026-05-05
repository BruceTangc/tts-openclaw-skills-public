#!/usr/bin/env bash
# Self-Learning Session-Start Hook
# Installed by: skills/self-improvement/hooks/openclaw/
# Runs at session start to check pending learnings and verifications.
#
# Enable: openclaw hooks enable self-improvement

HOOK_NAME="self-improvement"
LEARNING_TRAIL="$OPENCLAW_WORKSPACE/memory/.learning-trail.json"

if [ ! -f "$LEARNING_TRAIL" ]; then
    exit 0
fi

# Check for pending high-priority items
HIGH=$(python3 -c "
import json
try:
    with open('$LEARNING_TRAIL') as f:
        t = json.load(f)
    high = [e for e in t.get('entries', [])
            if e.get('priority') in ('critical','high') and e.get('status') == 'pending']
    print(len(high))
except:
    print(0)
" 2>/dev/null)

# Check for verifications due
DUE=$(python3 -c "
import json
from datetime import datetime
try:
    with open('$LEARNING_TRAIL') as f:
        t = json.load(f)
    due = [c for c in t.get('changes', [])
           if not c.get('verified') and c.get('next_check')
           and datetime.strptime(c['next_check'],'%Y-%m-%d') <= datetime.now()]
    print(len(due))
except:
    print(0)
" 2>/dev/null)

# Report if anything needs attention
SUMMARY=""
if [ "$HIGH" -gt 0 ] && [ "$HIGH" -le 5 ]; then
    SUMMARY="$HIGH pending high-priority items"
fi
if [ "$DUE" -gt 0 ]; then
    [ -n "$SUMMARY" ] && SUMMARY="$SUMMARY, "
    SUMMARY="${SUMMARY}$DUE verifications due"
fi

if [ -n "$SUMMARY" ]; then
    echo "🧠 [self-learning] $SUMMARY — run 'openclaw skills learn --cycle' to review"
fi
