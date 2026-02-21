---
name: kit_commands
description: Show Kit's full command reference guide.
user-invocable: true
---

# Kit Commands Reference

When this skill is invoked, reply with the following command reference. Do not add or remove anything — send it exactly as written:

## 🗂️ Session Management

• `/new` — Start a fresh session (clears context, I wake up fresh)
• `/reset` — Same as `/new`
• `/compact [instructions]` — Summarize old context to free up space. Add custom instructions like `/compact focus on the code discussion`
• `/stop` — Immediately abort whatever I'm doing (also stops subagents). Plain "stop" or "abort" works too

## ⚙️ Options & Directives

These work standalone OR mixed into a message (e.g., "explain quantum physics /think high"):

• `/model <provider/model>` — Switch AI model. Alone = show current model info
• `/models [provider]` — Browse available models (button menus on Telegram)
• `/think <level>` — Thinking depth: off, minimal, low, medium, high, xhigh (aliases: `/thinking`, `/t`)
• `/verbose on|off` — Show/hide extra detail (alias: `/v`)
• `/reasoning on|off|stream` — Show/hide internal reasoning (alias: `/reason`)
• `/elevated on|off|ask|full` — Toggle elevated exec permissions (alias: `/elev`)
• `/usage [off|tokens|full|cost]` — Usage stats in footers, or `/usage cost` for spending summary
• `/exec host=... security=... ask=...` — Set exec defaults for the session
• `/queue <mode> [debounce] [cap] [drop]` — Adjust message queue behavior

## 📊 Status & Info

• `/status` — Current session: model, context usage, thinking level, tokens
• `/whoami` — Your Telegram user ID, username, chat info (alias: `/id`)
• `/context` — How the context window is built, what's in it, how full
• `/help` — Quick command reference
• `/commands` — Full paginated list of every command

## 🛠️ Management

• `/allowlist [list|add|remove] [dm|group]` — View/edit who can talk to me
• `/approve <id> allow|deny` — Approve/deny pending exec requests
• `/subagents [list|stop|log|info|send]` — Manage background subagent runs
• `/config [show|set|unset] <path> [value]` — Edit openclaw.json live (needs `commands.config=true`)
• `/debug [show|set|unset|reset] <path> [value]` — Temporary runtime overrides (needs `commands.debug=true`)
• `/activation mention|always` — Group chats: respond to everything vs. only when mentioned
• `/send on|off|inherit` — Control whether I can reply in this session
• `/restart` — Restart OpenClaw (needs `commands.restart=true`)

## 🎵 Media & Tools

• `/tts [on|off|status|help|provider|limit|summary|audio]` — Full TTS control
• `/skill <name> [input]` — Run a skill directly
• `/bash <command>` — Run a shell command (also `!command` shorthand)

## 💡 Tips

• Directives stack — `/think high /model opus` right in a normal message
• `!` shorthand — `!ls -la` = `/bash ls -la`
• Model switching — `/model` alone = current info; `/model opus` = alias switch; `/models` = browse all
• Abort shortcuts — Just say "stop" or "abort" mid-generation
• `/kit_commands` — This reference! 🛠️
