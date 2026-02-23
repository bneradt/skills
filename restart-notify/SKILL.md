---
name: restart-notify
description: "Set up restart notifications so the user knows when OpenClaw restarts. Use when: user asks to be notified on restart, wants restart alerts, or says they don't know when openclaw restarts."
metadata: { "openclaw": { "emoji": "🔄" } }
---

# Restart Notifications

Configures OpenClaw to send a message whenever the gateway restarts — covering CLI restarts, systemd/launchd restarts, and crash recovery. Agent-triggered restarts (via the `gateway` tool) already notify via the restart sentinel; this covers everything else.

## How It Works

The `boot-md` bundled hook fires on every `gateway:startup` event and runs `~/.openclaw/workspace/BOOT.md` as an agent prompt. The agent executes the BOOT.md instructions and can use the `message` tool to send a notification. The boot run is silent — only the explicit `message` tool call reaches the user.

## Setup Steps

### 1. Enable internal hooks

Ensure `hooks.internal.enabled` is `true` in `~/.openclaw/openclaw.json`:

```json
{
  "hooks": {
    "internal": {
      "enabled": true
    }
  }
}
```

Read the config file first, merge this into the existing `hooks` section — do not overwrite other hook settings.

### 2. Create or update BOOT.md

Create `~/.openclaw/workspace/BOOT.md` with restart notification instructions. If BOOT.md already exists, **append** the restart notification section — do not overwrite existing content.

#### BOOT.md template for restart notification

```markdown
## Restart Notification

Send a restart notification to the owner:
- action: send
- channel: telegram
- target: <owner's Telegram user ID from config — check channels.telegram.allowFrom>
- message: "OpenClaw restarted."
```

Look up the owner's Telegram user ID from `channels.telegram.allowFrom` in `~/.openclaw/openclaw.json` and substitute it into the `target` field.

### 3. Message tool syntax

During boot execution, the agent has access to the `message` tool. Use it as:

- `action`: `send`
- `channel`: `telegram` (or whichever channel the user prefers)
- `target`: the user's ID on that channel (e.g. Telegram user ID)
- `message`: the notification text (e.g. `"OpenClaw restarted."`)

Use the `target` parameter (not `to`) for the recipient.

## When to Use

- User says "notify me when you restart"
- User says "I don't know when you restart"
- User asks for restart alerts or boot notifications
- User wants to know when OpenClaw comes back after a crash

## When NOT to Use

- One-time manual restarts via the `gateway` tool — the restart sentinel already sends a completion message back to the session that triggered it
- User just wants to restart OpenClaw — use the `gateway` tool instead
