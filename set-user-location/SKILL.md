---
name: set-user-location
description: "Set the user's default location for weather, astronomy, and other location-aware skills. Use when: user says 'set my location', 'I moved to…', 'my location is…', or 'change my city to…'."
metadata: { "openclaw": { "emoji": "📍" } }
---

# Set User Location

Sets the `USER_LOCATION` environment variable in the OpenClaw config so location-aware skills (weather, astronomy) pick it up automatically.

## How to Set

Edit `~/.openclaw/openclaw.json` and add or update the `env.vars.USER_LOCATION` value:

```json
{
  "env": {
    "vars": {
      "USER_LOCATION": "Savoy, IL"
    }
  }
}
```

The value should be a city/state or city/country string (e.g. `"Cape Coral, FL"`, `"London, UK"`).

### Steps

1. Read `~/.openclaw/openclaw.json`
2. Ensure the `env` and `env.vars` keys exist
3. Set `env.vars.USER_LOCATION` to the requested location
4. Write the file back (preserve all other keys)
5. Confirm the change to the user

### Important

- Do NOT overwrite other keys in `env.vars` — merge the new value in
- Do NOT overwrite other top-level config sections — only touch `env.vars`
- If the file doesn't exist yet, create it with just the `env.vars` section
- The gateway will pick up the change on next config reload (automatic via file watcher)

## When to Use

- "Set my location to Cape Coral, FL"
- "I'm in Tokyo now"
- "Change my default city to Chicago"
- "My location is Savoy, IL"

## When NOT to Use

- User passes a location directly to a skill (e.g. "weather in NYC") — no config change needed
- User asks what their location is — just read the config, don't modify it
