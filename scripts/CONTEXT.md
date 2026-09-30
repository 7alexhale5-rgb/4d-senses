# Scripts — media perception tools

## Inputs

- Working: `scripts/watch-video.py` (video URL/file → frame+audio perception),
  `scripts/transcribe-gemini.py` (audio file → transcript).
- Stable reference: `GEMINI_API_KEY` / `GROQ_API_KEY` env or `~/.claude/secrets/*.env`
  (documented in root `CLAUDE.md`).
- Entry condition: a video/audio perception request, or `hooks/4d-auto-vision.py` invoking
  `watch-video.py` in the background.
- Missing input (no API key): the script must degrade, not crash — auto-vision still detects
  the URL but analysis is degraded, per root `CLAUDE.md`.

## Process

1. Video: `python3 scripts/watch-video.py <URL> [--depth shallow|normal|deep]`.
2. Audio: `python3 scripts/transcribe-gemini.py <file> [--output path.md]` — run manually, not
   auto-fired.
3. Keep both scripts' CLI flags in sync with the table in root `CLAUDE.md` — that table is the
   contract other agents read before calling these scripts.

## Outputs

- Transcript/analysis text to stdout, or to `--output path.md` when given for transcription.
- Results are stored locally. Enabled Gemini video analysis uploads the video;
  Gemini transcription uploads audio. Groq transcription sends extracted audio.
  These provider calls transmit media off this machine; local storage is a separate rule.

## Human check

Alex spot-checks one video run and one audio run against the source media. Pass: transcript or
scene description matches what he saw/heard. Fail: file a finding against the failing script;
no separate log file to update.
