# Media Routing Table

When ANY media is shared, route through this decision tree:

```
INPUT DETECTED
     │
     ├── Video URL (YouTube/IG/TikTok/X/Loom)
     │   → python3 ~/.claude/scripts/watch-video.py <URL> [--depth shallow|normal|deep]
     │   → Auto-fires via 4d-auto-vision.py hook on UserPromptSubmit
     │
     ├── Local video file (.mp4/.mov/.webm/.mkv)
     │   → python3 ~/.claude/scripts/watch-video.py <path>
     │
     ├── Audio file (.m4a/.mp3/.wav/.flac/.ogg)
     │   → Transcript: python3 ~/.claude/scripts/transcribe-gemini.py <path>
     │   │   (~60s per hour of audio, no rate limits, no chunking)
     │   → Diarization (WHO said what): python3 ~/.claude/scripts/diarize-audio.py <path>
     │   → Batch: python3 ~/.claude/scripts/transcribe-gemini.py --batch <dir>
     │
     ├── Screen recording (.mov from Mac)
     │   → /watch-recording skill (ScreenMind MCP)
     │
     ├── Photo/screenshot (.jpg/.png/.webp)
     │   → Claude native vision (Read tool)
     │
     ├── PDF/document
     │   → Claude native (Read tool, pages: "1-5" for large)
     │
     ├── URL/article
     │   → Tier 1: Firecrawl MCP (primary — AI extraction, Markdown out)
     │   → Tier 2: defuddle skill (clean extraction, no JS)
     │   → Tier 2.5: stealth-fetch.py (Cloudflare/anti-bot bypass)
     │   │   python3 ~/.claude/scripts/stealth-fetch.py <URL> [--format md]
     │   │   Triggers: Firecrawl 403/empty, Cloudflare-protected, "stealth scrape"
     │   → Tier 3: Playwright MCP (JS-rendered/auth-required)
     │   → Tier 4: WebSearch (find cached/mirrored version)
     │
     └── Text/paste
         → Claude native
```

## Output Locations

| Tool | Output |
|------|--------|
| watch-video.py | `/tmp/video-intelligence/<id>/` — transcript.txt, frames/, report.md |
| diarize-audio.py | JSON to stdout — speaker-labeled timestamped segments |
| transcribe-gemini.py | stdout (single) or `--output-dir <dir>/*.md` (batch) |
| stealth-fetch.py | stdout (markdown/html/text) |
| ScreenMind | Via MCP — keyframes, OCR, timeline |

## Depth Levels (watch-video.py)

| Depth | What You Get | Speed |
|-------|-------------|-------|
| `shallow` | Transcript + 5 frames | ~10s |
| `normal` | Transcript + diarization + 10 frames + scenes | ~30s |
| `deep` | Transcript + diarization + 25 frames + emotion + faces | ~60s |

## Stealth Fetch (Tier 2.5 — Anti-Bot Bypass)

When Firecrawl returns 403, empty content, or hits Cloudflare:

```bash
# Default: full stealth with Cloudflare bypass
python3 ~/.claude/scripts/stealth-fetch.py <URL>

# Lighter: browser rendering without stealth (for SPAs)
python3 ~/.claude/scripts/stealth-fetch.py <URL> --dynamic

# Fastest: HTTP only with TLS fingerprinting (no browser)
python3 ~/.claude/scripts/stealth-fetch.py <URL> --fast

# Extract specific content
python3 ~/.claude/scripts/stealth-fetch.py <URL> --selector "article.content"

# Output as HTML instead of markdown
python3 ~/.claude/scripts/stealth-fetch.py <URL> --format html
```

**Auto-fallback**: If StealthyFetcher fails, automatically retries with DynamicFetcher.

**Bypasses**: Cloudflare Turnstile/Interstitial, PerimeterX, Akamai, basic bot detection.

**Speed**: ~3-5s (browser startup + page load + optional CF solve). Use `--fast` for ~1s HTTP-only.

## Per-Project Full Scrapling MCP (Optional)

For heavy scraping projects, enable the full 6-tool Scrapling MCP server:

```json
// Project .claude/settings.json
{
  "mcpServers": {
    "scrapling": { "command": "scrapling", "args": ["mcp"] }
  }
}
```

Tools: `get`, `bulk_get`, `fetch`, `bulk_fetch`, `stealthy_fetch`, `bulk_stealthy_fetch`

## API Keys Required

| Key | Location | Required For |
|-----|----------|-------------|
| `GEMINI_API_KEY` | `~/.claude/secrets/gemini.env` | Video perception (Gemini 2.5 Flash) |
| `GROQ_API_KEY` | `~/.claude/secrets/groq.env` | Audio transcription (Whisper) |
| `HF_TOKEN` | `~/.claude/secrets/huggingface.env` | Speaker diarization (pyannote) |
