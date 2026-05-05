---
name: self-improvement
description: Autonomous memory and self-learning system for AI agents. Continuously collects experience, manages memory (daily logs, user preferences, knowledge extraction), extracts principles, auto-adjusts behavior, and verifies improvements. Proposes actionable changes for user review before applying. Use when: (1) Agent needs to learn from past sessions, (2) User asks "improve yourself" or "learn from this", (3) Periodic self-evaluation is needed, (4) Agent needs to auto-correct recurring mistakes, (5) Updating AGENTS.md/SOUL.md/MEMORY.md/TOOLS.md based on experience, (6) Extracting universal principles from episodic experiences, (7) Processing user feedback to permanently adapt behavior, (8) Managing daily memory logs, user preferences, or knowledge retention.
---

# Self-Learning System

A continuous learning loop that automatically captures learnings, tracks improvements, and verifies their effectiveness.

**Inspiration:** This skill fuses the structured recording format and detection triggers from [pskoett/self-improving-agent](https://clawhub.ai/pskoett/self-improving-agent) (6.1k installs) with a verification/hypothesis loop that most agent learning systems lack.

## Learning Loop

```
Session / Task
    ↓
  [DETECT]     ← Automatic triggers: corrections, errors, feature requests
    ↓
  [LOG]        ← Structured entries with IDs, priorities, categories
    ↓
  [EXTRACT]    ← Distill patterns from repeated entries
    ↓
  [PROMOTE]    ← To AGENTS.md / SOUL.md / TOOLS.md / MEMORY.md
    ↓
  [VERIFY]     ← 7-day check: did this change actually help?
    ↓
  [ADAPT]      ← Reinforce success, revert failure
    ↓
  (back to detect on next interaction)
```

## Memory Management

The skill also manages the agent's memory system — daily logs, user preferences, and knowledge retention.

### Memory Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MEMORY LAYERS                         │
├──────────────┬──────────────┬──────────────┬────────────┤
│  raw         │  structured  │  distilled   │  injected  │
│  memory/*.md │  .learning-  │  MEMORY.md   │  every     │
│  (daily log) │  trail.json  │  USER.md     │  session   │
└──────────────┴──────────────┴──────────────┴────────────┘
```

### Auto-Daily-Log

At the end of each significant task or session, automatically append to `memory/YYYY-MM-DD.md`:

```markdown
### ✅ 10:30 - Task description
### ❌ 10:35 - Error: brief description
### 💡 10:40 - Insight: what was learned
### 📌 10:45 - User preference: user said X
```

Keep entries short (1-2 lines). Don't log every tool call — only significant events.

### Memory Types

| Type | Where | Example |
|------|-------|---------|
| **Daily events** | `memory/YYYY-MM-DD.md` | "10:30 创建 self-improvement skill" |
| **User preferences** | `USER.md` | "用户喜欢直接回答，不要解释" |
| **Knowledge facts** | `MEMORY.md` | "QWeather 需要自定义 Host" |
| **Behavioral principles** | `MEMORY.md` | "Simple before powerful" |
| **Tool notes** | `TOOLS.md` | "优先用 read 而不是 exec 读文件" |
| **Structured learning** | `.learning-trail.json` | 所有 LRN/ERR/FEAT 条目 |

### Memory Retention

| Memory | Retention | Action |
|--------|-----------|--------|
| Daily logs | Keep forever | Append-only, never delete |
| Learning entries | 90 days | Auto-resolve pending items after 90d |
| Verified principles | Keep forever | Part of long-term knowledge |
| User preferences | Keep until changed | Update when user says otherwise |
| Tool notes | Keep until outdated | Update when tools change |

### Memory Search

When user asks "之前说过什么" or "帮我回忆一下":

1. First check `MEMORY.md` (distilled knowledge)
2. Then check `USER.md` (preferences)
3. Then `grep` recent `memory/*.md` files
4. Then check `.learning-trail.json` for structured entries

### Memory Flow

```
会话中
  → 检测到用户偏好 / 知识 / 错误
  → 同时写入 memory/YYYY-MM-DD.md（原始）和 .learning-trail.json（结构化）
  
心跳/空闲
  → 读取 .learning-trail.json 的 patterns
  → 达到阈值的晋升为 MEMORY.md 原则或 USER.md 偏好
  
新会话开始
  → MEMORY.md 自动注入上下文
  → .learning-trail.json 的 watchlist 提醒我注意
```

## Auto-Trigger Points

### Detection Triggers

Automatically log when you notice:

**Corrections** → log to LEARNINGS.md (category: correction)
- "No, that's not right..."
- "Actually, it should be..."
- "You're wrong about..."
- "That's outdated..."
- User explicitly correcting your output

**Feature Requests** → log to FEATURE_REQUESTS.md
- "Can you also..."
- "I wish you could..."
- "Is there a way to..."
- "Why can't you..."

**Knowledge Gaps** → log to LEARNINGS.md (category: knowledge_gap)
- User provides info you didn't know
- Documentation you referenced is outdated
- API behavior differs from your understanding

**Errors** → log to ERRORS.md
- Command returns non-zero exit code
- Exception or stack trace
- Timeout or connection failure

**Successes** → log to LEARNINGS.md (category: best_practice)
- Found a better approach
- Quicker way to do something
- Cleaner pattern emerged

### Scheduled Triggers

| Trigger | When | Action |
|---------|------|--------|
| **Session end** | After completion | Auto-log summary to memory/YYYY-MM-DD.md |
| **Heartbeat** | Idle time | Run learn.py --cycle: check verifications, promote patterns |
| **Improve yourself** | On demand | Full cycle + report |
| **Hook** | Session start | If hook installed, review pending learnings |

## Structured Log Format

Every entry uses this format (inspired by pskoett standard):

### Learning Entry (LEARNINGS.md / auto-log)

```
## [LRN-YYYYMMDD-XXX] category:brief_title

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | in_progress | resolved | wont_fix | promoted
**Area**: frontend | backend | infra | tests | docs | config | behavior | tooling

### Summary
One-line description

### Details
What happened, what was wrong, what's correct

### Suggested Action
Specific fix or improvement

### Metadata
- Source: conversation | error | user_feedback | self_discovery
- Related Files: path/to/file
- Tags: tag1, tag2
- Pattern-Key: unique_key_for_dedup (optional, for recurring patterns)
- Recurrence-Count: 1
- First-Seen: YYYY-MM-DD
- Last-Seen: YYYY-MM-DD
```

### Error Entry (ERRORS.md)

```
## [ERR-YYYYMMDD-XXX] tool_or_command_name

**Logged**: ISO-8601 timestamp
**Priority**: high
**Status**: pending
**Area**: infra | tooling | config

### Summary
Brief description of what failed

### Error
Actual error message or output

### Context
- Command/operation attempted
- Input or parameters used

### Suggested Fix
What might resolve this

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file
- See Also: ERR-YYYYMMDD-XXX (if recurring)
```

### Feature Request Entry (FEATURE_REQUESTS.md)

```
## [FEAT-YYYYMMDD-XXX] capability_name

**Logged**: ISO-8601 timestamp
**Priority**: medium
**Status**: pending
**Area**: as appropriate

### Summary
What the user wanted to do

### User Context
Why they needed it

### Complexity Estimate
simple | medium | complex

### Metadata
- Frequency: first_time | recurring
- Related Features: existing_feature_name
```

### ID Generation

Format: `TYPE-YYYYMMDD-XXX`
- TYPE: LRN (learning), ERR (error), FEAT (feature)
- YYYYMMDD: Current date
- XXX: Sequential number or random 3 chars (e.g., 001, A7B)

**Where to log:** The agent logs structured entries to `memory/.learning-trail.json` (structured, queryable). The helper scripts also write human-readable copies to `.learnings/` files if they exist.

## Recurring Pattern Detection

When logging something that might already exist:

1. Search `.learning-trail.json` for matching Pattern-Key
2. If found: increment Recurrence-Count, update Last-Seen
3. If not found: create new entry with Recurrence-Count: 1

### Promotion Rule

Promote a pattern to workspace core files when **all** are true:
- Recurrence-Count >= 3
- Seen across at least 2 distinct sessions
- Occurred within a 30-day window

**Promotion targets:**

| Entry Type | Promote To | Example |
|-----------|-----------|---------|
| Behavioral pattern | SOUL.md | "Be concise, skip disclaimers" |
| Workflow improvement | AGENTS.md | "Spawn sub-agents for long tasks" |
| Tool gotcha | TOOLS.md | "Git push needs auth configured" |
| User preference | USER.md | "User prefers direct answers" |
| Universal principle | MEMORY.md | "Simple before powerful" |

## Verification Loop

When a change is promoted or applied, record a verification entry:

```json
{
  "id": "change-20260505-001",
  "source": "LRN-20260505-003",
  "target": "TOOLS.md",
  "change": "Added 'prefer read over exec for files'",
  "hypothesis": "This will reduce file-viewing errors",
  "verified": false,
  "next_check": "2026-05-12",
  "evidence": []
}
```

After 7 days, `learn.py --cycle` checks:
- Did the error rate drop for the addressed issue?
- Was the change relevant to the root cause?
- Did the change cause any regressions?

**Verification outcomes:**

| Result | Action |
|--------|--------|
| ✅ Confirmed effective | Mark verified, reduce monitoring to monthly |
| ❌ Ineffective | Revert change, log why it failed |
| ❌ Made worse | Revert immediately, escalate |
| ❓ Inconclusive | Extend monitoring, add more data points |

## Verification Script

```bash
python3 scripts/learn.py --cycle     # Full cycle: check verifications + promote patterns
python3 scripts/learn.py --verify    # Only check pending verifications
python3 scripts/learn.py --status    # Show learning stats
```

## Hook Integration (Session Start)

For automatic reminders at session start, install the hook:

```bash
# Copy hook template
cp -r skills/self-improvement/hooks ~/.openclaw/hooks/self-improvement

# Enable it
openclaw hooks enable self-improvement
```

The hook checks `.learning-trail.json` on session start for:
- Pending high-priority items
- Verifications due for review
- Patterns ready for promotion

## Quick Reference

| Situation | Action |
|-----------|--------|
| Command/operation fails | Log to ERRORS.md + auto-log |
| User corrects you | Log to LEARNINGS.md (correction) |
| User wants missing feature | Log to FEATURE_REQUESTS.md |
| API/external tool fails | Log to ERRORS.md |
| Knowledge was outdated | Log to LEARNINGS.md (knowledge_gap) |
| Found better approach | Log to LEARNINGS.md (best_practice) |
| Same error 3x across sessions | Promote to core file |
| Change applied 7+ days ago | Run verification check |

## Priority Guidelines

| Priority | When to Use |
|----------|-------------|
| **critical** | Blocks core functionality, data loss risk, security issue |
| **high** | Significant impact, affects common workflows, recurring issue |
| **medium** | Moderate impact, workaround exists |
| **low** | Minor inconvenience, nice-to-have |

## Conflict Resolution

When two principles contradict, the system uses **priority scoring** to decide which wins:

```
Score = BasePriority(100/60/30/10) + RecurrenceBonus(×10 each) + RecencyBonus(up to 30) + AreaWeight(up to 50)

Highest score wins.
```

Example conflict:
- "Use headless browser for automation" (tooling, score: 85)
- "Show browser window for demos" (behavior, score: 40)
- **Winner:** headless automation (85 > 40)

When a tie is detected, the system logs it for human review.

## Forgetting Mechanism

Old learnings that aren't reinforced automatically fade:

| Time without reinforcement | Action |
|---------------------------|--------|
| 30 days | Priority demoted one level (high→medium, etc.) |
| 60 days | Priority → low, flagged as stale |
| 90 days | Auto-resolved as `wont_fix` |

Reinforcement happens when:
- The same error pattern reoccurs → Recurrence-Count increases → freshness reset
- The agent actively references the principle → logged in evidence
- User confirms the learning is still relevant

## Auto-Revert

When a verification is overdue by 7+ days without evidence:

| Overdue | Action |
|---------|--------|
| 7 days | Grace period — reminder only |
| 14 days | First extension + evidence request |
| 21+ days | Auto-revert: change undone, logged as `auto_reverted` |

The revert is safe because all changes are file-based (TOOLS.md, USER.md, etc.) and the old state is tracked in the learning trail.

## Proposal Workflow

When the learning system detects a pattern ready for promotion or a change that needs verification, it generates a **proposal** for user review:

```
Pattern detected (≥3x across ≥2 sessions)
    ↓
Generate proposal: what to change, why, risk level
    ↓
Present to user for approval
    ↓
User says "approve N" or "skip N"
    ↓
Apply approved changes, track for verification
```

### Proposal Format

Each proposal includes:
- **Type**: promotion / verification / critical_fix
- **Target**: Which file to change (TOOLS.md, MEMORY.md, SOUL.md, AGENTS.md)
- **Change**: Specific text to add/modify
- **Motivation**: Why this change (pattern evidence)
- **Risk**: Low (adds info) / Medium (changes behavior)
- **Effort**: low / medium / high
- **Impact**: low / medium / high

### Auto-apply vs Propose

| Change Type | Action | Example |
|-----------|--------|---------|
| Add note to TOOLS.md | ✅ Auto-apply | "QWeather needs custom host" |
| Add principle to MEMORY.md | ✅ Auto-apply | "Simple before powerful" |
| Add preference to USER.md | ✅ Auto-apply | "User prefers direct answers" |
| Add guideline to SOUL.md | ⚠️ Propose | "Be concise, skip disclaimers" |
| Add rule to AGENTS.md | ⚠️ Propose | "Spawn sub-agents for long tasks" |
| Create new skill | ❌ Always ask | New skill for recurring task |

### Usage

```bash
python3 scripts/learn.py --propose    # Generate proposals for review
```

The agent will present proposals and wait for your approval before applying.

## Key Principles

1. **Learn automatically.** The system should work without being told.
2. **Verify or it didn't happen.** Every change must be checked later.
3. **Reversible first.** Always track old state so changes can be undone.
4. **Patterns over anecdotes.** One error is noise. Three identical errors are a pattern.
5. **Structured over freeform.** Standardized IDs and categories make learnings searchable.
6. **Don't log secrets.** Never write tokens, keys, or full source files.
7. **Don't learn from noise.** Not every interaction is a learning opportunity.

## References

- [reflection_frameworks.md](references/reflection_frameworks.md) — Detailed frameworks and patterns
- [scripts/learn.py](scripts/learn.py) — Learning cycle engine
- [scripts/reflect.py](scripts/reflect.py) — Session data collector + auto-log
- [hsoks/](hooks/) — OpenClaw session-start hook template
