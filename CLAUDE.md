# racetrace

## Git workflow

- `dev` is the long-lived integration branch. Never commit to it directly.
- Each feature or fix gets its own branch cut from `dev`, and lands in `dev` only by merging a PR.
- `main` is for releases only. Merge `dev` into `main` only when cutting a release; never commit or open feature PRs directly against `main`.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `CONTEXT.md` plus `docs/adr/`. See `docs/agents/domain.md`.
