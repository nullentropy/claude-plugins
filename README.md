# nullentropy

`ne`, a Claude Code plugin for one way of working: discovery before building, review before every PR, and long work kept in a shared record.

| Skill | What it does |
|---|---|
| `mentat` | Discovery: agrees with the user how a feature should work before it is built |
| `truthsayer` | Reviews a branch with the `gom-jabbar` agent, fixes what it finds, records a clean verdict |
| `voice` | How docs, PRs, commits, comments, tickets and pages are written |
| `sietch` | A track's shared record on the branch `sietch/<name>`: job, orders, progress, next steps |
| `navigator` | Proposes the next units of work and writes their briefs |
| `fedaykin` | Dispatches a unit to a cloud session or a local agent with a self-contained prompt |
| `swordmaster` | Takes open PRs to green: conflicts, CI, every review thread answered and resolved |
| `water` | Budgets a track against the weekly limit, from the status line or the user's readings |
| `spice` | Reports which units reached production, and the yield per percent of the weekly limit |

Hooks:

- Code edits on a branch are refused until its work is classified by `mentat` or a recorded skip.
- `gh pr create` and `gh pr ready` are refused until `truthsayer` records a clean review of HEAD, unless the user says "skip review".
- The reply style is restated on every prompt; the working rules and the repository's tracks at session start.
- The account's 5-hour and weekly usage is added to every prompt, when the status line below keeps it.

Gate records live in `~/.local/state/ne` (or `$NE_STATE`), outside every repository.

Install:

```
claude plugin marketplace add nullentropy/claude-plugins
claude plugin install ne@nullentropy
```

Claude Code gives usage limits only to the status line command, so the limits hook and `water` need
`plugins/ne/statusline.sh` as the status line. Copy it somewhere stable, such as `~/.claude/hooks/`, and set
`"statusLine": {"type": "command", "command": "<that path>"}` in `settings.json` in each config dir you use.

Try it without installing: `claude --plugin-dir plugins/ne`.
