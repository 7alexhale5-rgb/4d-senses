---
description: Show active senses, recent pain history, and alert summary
argument-hint: Optional time range (e.g., "last hour", "today")
---

# /senses-status

Show the current state of 4D Senses perception.

## What to Show

### 1. Active Senses
List which senses are active in this session:
- **Sense 8 (Smell)**: Code quality detection on Edit/Write — god files, nesting, duplication, secrets, console.log, TODOs
- **Sense 10 (Pain)**: Failure tracking on Edit/Write/Bash — severity accumulation, repeated failure detection
- **Sense 15 (Intuition)**: Pattern matching on Edit/Write/Bash — matches current work against your past feedback memories
- **Auto-Vision**: Video URL detection on every prompt — auto-fires video perception pipeline

### 2. Pain History
Read the pain log from the plugin data directory:

```bash
# Find and display pain log
DATA_DIR="${CLAUDE_PLUGIN_DATA:-$HOME/.local/share/claude-senses}"
PAIN_LOG="$DATA_DIR/pain-log.json"
```

If the pain log exists, show:
- Total pain events (last 24 hours)
- Top 3 pain types by frequency
- Most recent pain event (time, type, severity)
- Session pain severity total (last 30 min)

If no pain log exists, show: "No pain events recorded yet. This is a good thing."

### 3. Intuition Context
Check for feedback memory files in the current project's memory directory:
```bash
PROJECT_KEY=$(pwd | sed 's/\//-/g' | sed 's/^-//')
MEMORY_DIR="$HOME/.claude/projects/$PROJECT_KEY/memory"
```

Count feedback_* files and show:
- Number of feedback memories loaded
- Last updated date
- "These memories inform Sense 15 (Intuition) pattern matching."

### 4. Dependencies
Check which optional dependencies are available:
- `python3` — required for Auto-Vision
- `yt-dlp` — required for video download
- `ffmpeg` — required for video processing
- `GEMINI_API_KEY` — required for Gemini transcription (check if set in environment)

For missing dependencies, show what features are degraded.

## Output Format

Present as a clean summary, not raw JSON. Use simple formatting:

```
4D Senses — Status
━━━━━━━━━━━━━━━━━━

Active Senses: 4/4
  ✓ Smell (PostToolUse Edit|Write)
  ✓ Pain (PostToolUse Edit|Write|Bash)
  ✓ Intuition (PostToolUse Edit|Write|Bash)
  ✓ Auto-Vision (UserPromptSubmit)

Pain History (last 24h):
  3 events — TEST_FAILURE (2), COMMAND_ERROR (1)
  Session severity: 8/15 threshold

Intuition Context:
  7 feedback memories loaded
  Last updated: 2026-03-28

Dependencies:
  ✓ python3, yt-dlp, ffmpeg
  ✗ GEMINI_API_KEY not set (video perception degraded)
```
