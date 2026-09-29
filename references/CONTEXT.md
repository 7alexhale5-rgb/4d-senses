# References — media routing contract

## Inputs

- Working: `references/media-routing.md` — the decision tree for video URL / audio file /
  photo / PDF.
- Stable reference: this file IS the stable reference other 4d-senses rooms and consuming
  projects (e.g. `evansville-tonight`) point to; it has no upstream input of its own beyond
  what ships in `hooks/4d-auto-vision.py` and `scripts/`.
- Entry condition: the routing table in root `CLAUDE.md` "Media Routing" section needs to
  change, or a new media type needs a route.

## Process

1. Edit `references/media-routing.md` first; then mirror the same row into root `CLAUDE.md`'s
   "Media Routing" table so a reader who only opens the router still sees the current routes.
2. Never add a route that isn't backed by a real script in `scripts/` or Claude's native Read
   tool (photo/PDF) — a routing row with no implementation is a broken promise to callers.

## Outputs

- `references/media-routing.md` — the one home for the routing decision tree.

## Human check

Alex confirms a real media drop (a video link, a screenshot) follows the documented row. Pass:
the right tool fires. Fail: correct the row and the mirrored `CLAUDE.md` table together.
