---
name: gmail-notify
description: "Set up priority Gmail notifications via the webhook hook pipeline. Use when: user wants email alerts, wants to configure Gmail filtering, or asks about the Gmail webhook/hook."
metadata: { "openclaw": { "emoji": "📬" } }
---

# Gmail Priority Notifications

Sends Telegram notifications for priority emails using a pre-filter script (`gmail-filter.sh`) that queries Gmail via `gog` and only wakes the agent when there are matching emails.

## Architecture

```
Gmail push (Pub/Sub) → gog watch serve → /hooks/gmail → hook mapping → gmail-filter.sh → agent summarizes → Telegram
```

The hook mapping triggers `gmail-filter.sh`, which queries Gmail for priority unread emails. If there are matches, the agent summarizes them and delivers via Telegram. If not, the agent returns `NO_REPLY`.

## Setup

### 1. Ensure the filter script executable

```bash
chmod +x ~/.openclaw/workspace/skills/gmail-notify/gmail-filter.sh
```

### 2. Hook mapping in openclaw.json

```json
{
  "hooks": {
    "mappings": [
      {
        "match": { "path": "gmail" },
        "action": "agent",
        "wakeMode": "now",
        "name": "Gmail Filter",
        "messageTemplate": "Gmail push received. Run the pre-filter script:\n\n```bash\nbash ~/.openclaw/workspace/skills/gmail-notify/gmail-filter.sh\n```\n\nIf exit code 1 (no output): reply EXACTLY with NO_REPLY\n\nIf JSON output: summarize each email for the user as a short Telegram message. For each email include:\n- **From** (person/org name, not the raw email)\n- **Subject**\n- **Summary** — 1-3 sentences covering the key content and any action items from the body\n\nKeep the overall message concise and scannable.",
        "deliver": true,
        "channel": "telegram",
        "thinking": "off"
      }
    ]
  }
}
```

### 3. Verify

```bash
bash ~/.openclaw/workspace/skills/gmail-notify/gmail-filter.sh
```

- Exit code 0 + JSON output = matching emails found
- Exit code 1 + no output = nothing to report

## Filter Criteria

The script queries for **unread** emails newer than the last checkpoint, matching ANY of:

1. **Primary inbox** — `in:inbox` excluding `category:promotions`, `category:updates`, `category:forums`
2. **label:Missionaries**
3. **label:"SPBC Prayer Chain"**
4. **Voice of the Martyrs** — `from:vom.org` or `from:persecution.com`

## Deduplication

The script tracks the last check time in `~/.openclaw/state/gmail-filter/last-check-epoch`. Each run:

1. Uses Gmail's `after:<epoch>` to only query emails newer than the last check.
2. Falls back to `newer_than:1h` on first run (no state file).
3. Updates the checkpoint after each run (newest email date, or "now" if no matches).

To reset: `rm ~/.openclaw/state/gmail-filter/last-check-epoch`

## Script Output

`gmail-filter.sh` uses `gog gmail messages search --include-body` and returns JSON with `from`, `subject`, `date`, `labels`, and `body` (truncated to 3000 chars) per message.

### Customizing

Edit `gmail-filter.sh` in this skill directory. The filter query is in the `QUERY` variable. Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOG_ACCOUNT` | `brian.neradt@gmail.com` | Gmail account |
| `GMAIL_FILTER_MAX` | `10` | Max messages to return |
| `GMAIL_FILTER_MAX_BODY` | `3000` | Max body chars per message |
| `GMAIL_FILTER_WINDOW` | `1h` | Fallback window (only used when no state file exists) |

## When to Use

- User wants to set up or modify Gmail email notifications
- User wants to change which emails trigger notifications
- User asks about the Gmail webhook or hook pipeline

## When NOT to Use

- User wants to send/read email directly — use the `gog` skill
- User wants to set up Gmail webhook from scratch — use `openclaw webhooks gmail setup`
