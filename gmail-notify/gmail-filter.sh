#!/usr/bin/env bash
# gmail-filter.sh — Pre-filter Gmail for priority emails before waking the agent.
#
# Runs on the Pi as part of the Gmail hook pipeline.
# Exits 0 with JSON on stdout when there are matching emails.
# Exits 1 (no output) when there is nothing to report.
#
# Tracks the newest email date in a state file to avoid duplicates.
# Falls back to "last 1 hour" on first run or if state is stale.
#
# Required env: GOG_KEYRING_BACKEND, GOG_KEYRING_PASSWORD, GOG_ACCOUNT
# (set these in openclaw.json → env.vars)

set -euo pipefail

ACCOUNT="${GOG_ACCOUNT:-brian.neradt@gmail.com}"
MAX="${GMAIL_FILTER_MAX:-10}"
FALLBACK_WINDOW="${GMAIL_FILTER_WINDOW:-1h}"
MAX_BODY="${GMAIL_FILTER_MAX_BODY:-3000}"
STATE_DIR="${HOME}/.openclaw/state/gmail-filter"
STATE_FILE="${STATE_DIR}/last-check-epoch"

mkdir -p "$STATE_DIR"

# Determine the time boundary: stored epoch or fallback
time_filter=""
if [ -f "$STATE_FILE" ]; then
  last_epoch=$(cat "$STATE_FILE" 2>/dev/null | tr -d '[:space:]')
  if [[ "$last_epoch" =~ ^[0-9]+$ ]] && [ "$last_epoch" -gt 0 ]; then
    time_filter="after:${last_epoch}"
  fi
fi

if [ -z "$time_filter" ]; then
  time_filter="newer_than:${FALLBACK_WINDOW}"
fi

# Priority filter query:
#   1. Primary inbox (exclude promotions/updates/forums)
#   2. label:Missionaries
#   3. label:"SPBC Prayer Chain"
#   4. Voice of the Martyrs (vom.org / persecution.com)
QUERY="is:unread ${time_filter} ((in:inbox AND -category:promotions AND -category:updates AND -category:forums) OR label:Missionaries OR label:\"SPBC Prayer Chain\" OR from:vom.org OR from:persecution.com)"

# Use messages search (not thread search) to get individual emails with body text
result=$(gog gmail messages search "$QUERY" --max "$MAX" --json --include-body --account "$ACCOUNT" 2>/dev/null)

# Check if any messages matched
msg_count=$(echo "$result" | jq '.messages | length')

if [ "$msg_count" -eq 0 ] || [ -z "$msg_count" ]; then
  # No matches — still update the checkpoint to "now"
  date +%s > "$STATE_FILE"
  exit 1
fi

# Truncate body text per message to keep output manageable
result=$(echo "$result" | jq --argjson max "$MAX_BODY" '
  .messages |= [.[] | .body = (.body[:$max] + if (.body | length) > $max then "…[truncated]" else "" end)]
')

# Update the checkpoint to the newest email's date
newest_date=$(echo "$result" | jq -r '.messages[0].date // empty')
if [ -n "$newest_date" ]; then
  newest_epoch=$(date -d "$newest_date" +%s 2>/dev/null || true)
  if [[ "$newest_epoch" =~ ^[0-9]+$ ]] && [ "$newest_epoch" -gt 0 ]; then
    echo "$newest_epoch" > "$STATE_FILE"
  fi
fi

echo "$result"
