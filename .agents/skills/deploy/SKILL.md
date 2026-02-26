---
name: deploy
description: "Codex deployment workflow for this skills repo to the OpenClaw host pi4brian_remote. Use when the user asks to commit/push local changes, pull ~/.openclaw/workspace/skills on the Pi, and restart the gateway."
---

# Deploy (pi4brian_remote)

This skill is for Codex (agent-side), not for OpenClaw runtime configuration.

Use it to deploy this local `skills` repo to `pi4brian_remote` and restart the OpenClaw gateway.

## Standard Workflow

1. Review and commit local changes

- `git status --short`
- Review only the intended diffs
- Commit with a clear message
- Push the current branch (usually `main`)

Do not include unrelated changes unless the user explicitly asks.

2. Update the repo on the Pi

Remote repo path:

- `~/.openclaw/workspace/skills`

Command:

```bash
ssh pi4brian_remote 'cd ~/.openclaw/workspace/skills && git pull --ff-only'
```

3. Restart the gateway (explicit binary path)

Command:

```bash
ssh pi4brian_remote '~/.local/bin/openclaw gateway restart'
```

The restart may take a few seconds. Wait for output and confirm success before reporting completion.

Typical success output:

- `Restarted systemd service: openclaw-gateway.service`

## Preferred One-Liner (after local push)

Use this when appropriate:

```bash
ssh pi4brian_remote 'cd ~/.openclaw/workspace/skills && git pull --ff-only && ~/.local/bin/openclaw gateway restart'
```

Still monitor the output to confirm the restart succeeds.

## Recent Deployment Observations

- `openclaw` may not be on `PATH` in non-interactive SSH shells. Use `~/.local/bin/openclaw`.
- Avoid relying on `zsh -lic` for the restart command; shell init can emit `can't change option: zle` in non-interactive sessions.
- The restart command may appear idle briefly before printing success output. Poll/wait instead of aborting immediately.
- If `git pull` succeeds but restart fails, run the restart command separately and report both outcomes clearly.

## Failure Handling

- `git pull --ff-only` fails:
  - Stop and report the non-fast-forward/conflict state; do not create a merge commit on the Pi.
- `command not found` for `openclaw`:
  - Use `~/.local/bin/openclaw gateway restart`.
- Restart output is missing or hangs unusually long:
  - Re-run the restart command separately and inspect service status/logs if needed.
