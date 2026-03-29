# 4D Senses

**Push-based quality awareness for Claude Code.** Local-first, auto-firing, learns from your mistakes.

The only Claude Code plugin that makes quality awareness reflexive — it fires automatically on every tool use, tracks failure patterns across your session, and matches your current work against your own past mistakes. No cloud accounts. No dashboards. Just a nervous system.

## What It Does

| Sense | Fires On | What It Detects |
|-------|----------|----------------|
| **Smell** | Every file edit/write | God files, deep nesting, line duplication, hardcoded secrets, console.log pollution, TODO accumulation |
| **Pain** | Every edit/write/bash | Failure severity tracking, repeated error detection ("3 errors in a row = wrong approach"), session pain accumulation |
| **Intuition** | Every edit/write/bash | Matches current work against your `feedback_*` memory files, pain deja vu, risky patterns, late-night warnings |
| **Auto-Vision** | Every prompt | Detects video URLs and auto-fires transcription + analysis in background |

## Install

```bash
claude plugin add 7alexhale5-rgb/4d-senses
```

That's it. All four senses activate immediately.

## Optional: Video Perception

For auto-vision to fully work, you need:

```bash
# Gemini API key (free tier, no rate limits)
export GEMINI_API_KEY="your-key-here"
# Get one at: https://aistudio.google.com/apikey

# Video tools
brew install yt-dlp ffmpeg  # macOS
# or: apt install yt-dlp ffmpeg  # Linux
```

Without these, the other three senses (smell, pain, intuition) work perfectly. Auto-vision will detect URLs but can't process video.

## How It Works

### Smell (Sense 8)
Fires on every `Edit` and `Write` tool use. Reads the modified file and checks for:
- **God files**: >500 lines for code, >1000 for config
- **Deep nesting**: >5 indentation levels
- **Duplication**: 3+ identical non-trivial lines
- **Secrets**: OpenAI-style keys, Bearer tokens, hardcoded passwords
- **Console pollution**: >5 `console.log` statements in JS/TS
- **Tech debt**: >3 TODO/FIXME/HACK markers

Output: Warnings injected into Claude's context as `FAINT`, `WHIFF`, or `STINKS` severity.

### Pain (Sense 10)
Fires on every `Edit`, `Write`, and `Bash` tool use. Tracks failure patterns:
- Categorizes Bash failures by severity (1-5 scale)
- Detects **repeated pain** — 3x same error type in 5 minutes triggers: *"STOP. Step back. Diagnose root cause before retrying."*
- Tracks **session pain accumulation** — severity 15+ in 30 minutes triggers a pause suggestion
- Logs critical file edits (settings.json, package.json, .env, migrations)

### Intuition (Sense 15)
Fires on every `Edit`, `Write`, and `Bash` tool use. The most novel sense — it reads your personal feedback memory files (`feedback_*.md` in your Claude Code project memory) and matches them against your current action:
- If keywords from the current file/command match past feedback, it surfaces the relevant lesson
- Detects **pain deja vu** — warns when you're working in an area that caused past failures
- Flags risky patterns: migrations, .env edits, rsync with --delete
- Late-night guard: warns when editing critical files between 1-5 AM

### Auto-Vision
Fires on every user prompt. Scans for video URLs (YouTube, Instagram, TikTok, X/Twitter, Loom, raw mp4/mov/webm) and automatically launches the video perception pipeline:
- Downloads via yt-dlp
- Analyzes via Gemini 2.5 Flash (native video understanding)
- Falls back to Groq Whisper for transcription
- Extracts key frames
- Output lands at `/tmp/video-intelligence/<id>/`

## Commands

### `/senses-status`
Shows the current state of all senses: which are active, recent pain history, loaded feedback memories, and dependency status.

## Architecture

All senses use Claude Code's **hook system** — they fire as PostToolUse or UserPromptSubmit events. This means:
- **Push-based**: Signals are injected into Claude's context automatically
- **Local-first**: All processing happens on your machine
- **Zero latency**: Hooks fire synchronously within 5s timeout
- **No MCP server**: Avoids context bloat from tool declarations

Data (pain logs, debounce state) is stored in the Claude Code plugin data directory — auto-managed, never leaves your machine.

## Comparison

| Feature | 4D Senses | VideoDB Pair Programmer | Screenpipe | claudewatch |
|---------|-----------|----------------------|-----------|-------------|
| Code quality awareness | Yes (7 patterns) | No | No | No |
| Failure tracking | Yes (severity + accumulation) | No | No | Yes (loops only) |
| Personal memory matching | Yes (your feedback files) | No | No | No |
| Auto-fire (no commands needed) | Yes (hooks) | No (explicit commands) | No (query-based) | Partial |
| Local-first | Yes | No (cloud required) | Yes | Yes |
| Video perception | Yes (auto on URLs) | Yes (screen + mic) | Yes (screen + audio) | No |

## Requirements

- Claude Code CLI
- Node.js (for JS hooks — bundled with Claude Code)
- Python 3 (for auto-vision + scripts)
- Optional: `yt-dlp`, `ffmpeg`, `GEMINI_API_KEY` for video perception

## License

MIT
