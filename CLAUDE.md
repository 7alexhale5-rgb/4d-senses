# 4D Senses — Push-Based Quality Awareness

This plugin gives Claude Code a nervous system — automatic quality signals that fire on every tool use without explicit invocation.

## Active Senses

| Sense | Event | Matcher | What It Detects |
|-------|-------|---------|----------------|
| **Smell** (sense-8) | PostToolUse | Edit\|Write | God files (>500 lines), deep nesting (>5 levels), line duplication (3+ repeats), hardcoded secrets, console.log pollution (>5), TODO accumulation (>3) |
| **Pain** (sense-10) | PostToolUse | Edit\|Write\|Bash | Bash failures by severity (1-5), repeated failures (3x same error in 5 min = "stop and rethink"), session pain accumulation, critical file edit logging |
| **Intuition** (sense-15) | PostToolUse | Edit\|Write\|Bash | Matches current file/command against your `feedback_*` memory files, pain deja vu, risky patterns (migrations, .env edits, rsync --delete), late-night critical file warnings |
| **Auto-Vision** (4d-auto-vision) | UserPromptSubmit | * | Detects video URLs (YouTube, Instagram, TikTok, X, Loom, raw video) and auto-fires the video perception pipeline in background |

## Media Routing

When media is shared, route through this decision tree:

| Input | Tool | Auto? |
|-------|------|-------|
| Video URL (YouTube/IG/TikTok/X/Loom) | `watch-video.py` (via auto-vision hook) | YES |
| Audio file (.m4a/.mp3/.wav) | `transcribe-gemini.py` | No — run manually |
| Photo/screenshot | Claude native vision (Read tool) | YES |
| PDF | Claude native (Read tool) | YES |

### Scripts

| Script | Location | Usage |
|--------|----------|-------|
| `watch-video.py` | `${CLAUDE_PLUGIN_ROOT}/scripts/watch-video.py` | `python3 <script> <URL> [--depth shallow\|normal\|deep]` |
| `transcribe-gemini.py` | `${CLAUDE_PLUGIN_ROOT}/scripts/transcribe-gemini.py` | `python3 <script> <file> [--output path.md]` |

### API Keys (Optional)

| Key | Purpose | Set via |
|-----|---------|---------|
| `GEMINI_API_KEY` | Video perception + transcription (Gemini 2.5 Flash) | Shell environment or `~/.claude/secrets/gemini.env` |
| `GROQ_API_KEY` | Whisper transcription fallback | Shell environment or `~/.claude/secrets/groq.env` |

Without these keys, auto-vision will detect URLs but video analysis will be degraded.

## Pain Thresholds

- **Single failure**: Logged silently (severity 1-2) or warned (severity 3+)
- **3x same error in 5 min**: "STOP. Step back. Diagnose root cause."
- **Session severity ≥ 15 in 30 min**: "SESSION PAIN ACCUMULATING — consider pausing"

## Data Storage

Pain logs and debounce state are stored in the plugin data directory (auto-managed by Claude Code). No data leaves your machine.
