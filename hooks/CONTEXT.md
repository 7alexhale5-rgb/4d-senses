# Hooks — the four senses

## Inputs

- Working: `hooks/hooks.json` (event → matcher → script wiring), each `sense-*.js` file,
  `hooks/4d-auto-vision.py`, `hooks/lib/skip-paths.js` (shared path-skip logic).
- Stable reference: `references/media-routing.md` for what auto-vision should route to.
- Entry condition: editing what fires on a tool-use event, or adding a fifth sense.
- Missing input (e.g. `hooks.json` absent): stop — the plugin has no registered hooks without it.

## Process

1. Add a new sense as `hooks/sense-<N>-<name>.js`; wire it into `hooks/hooks.json` under the
   right event (`PostToolUse` for smell/pain/intuition, `UserPromptSubmit` for auto-vision).
2. Match the existing severity/threshold shape documented in the root `CLAUDE.md` "Pain
   Thresholds" table before changing sense-10's numbers.
3. Route media detection changes through `hooks/4d-auto-vision.py`, which calls
   `scripts/watch-video.py` in the background — do not duplicate that call in a new hook.
4. `hooks/hooks.json.pre-wave1` is an untracked backup of the pre-wave1 wiring; leave it unless
   Alex asks to diff or restore from it.

## Outputs

- `hooks/hooks.json` — the live event wiring, read by Claude Code on every tool use.
- Pain/debounce state — written to the plugin data directory at runtime (auto-managed, not a
  file in this tree).

## Human check

Alex runs the plugin locally (fires an Edit/Write/Bash in a real session) and confirms the
sense fires with the right message and severity. Pass: behavior matches the CLAUDE.md table.
Fail: fix the matcher or threshold and re-test; no separate sign-off file.
