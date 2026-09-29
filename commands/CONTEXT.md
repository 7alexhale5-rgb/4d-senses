# Commands — slash commands

## Inputs

- Working: `commands/senses-status.md` (the `/4d-senses:senses-status` command definition).
- Stable reference: pain/debounce state in the plugin data directory the command reports on.
- Entry condition: adding a new operator-facing command, or changing what senses-status shows.

## Process

1. One command = one Markdown file in `commands/`, named for its slash-command id.
2. `senses-status` reads the plugin's runtime pain/debounce state and reports session severity
   per the thresholds in root `CLAUDE.md`; keep its output format in sync with that doc if the
   thresholds change.

## Outputs

- `commands/<name>.md` — the command Claude Code registers under `.claude-plugin/plugin.json`.

## Human check

Alex runs `/4d-senses:senses-status` in a session with known pain history and confirms the
numbers match. Pass: matches. Fail: fix the read path in the command file.
