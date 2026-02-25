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
LOCK_FILE="${STATE_DIR}/lock"

mkdir -p "$STATE_DIR"

# Serialize runs: Gmail Pub/Sub can emit multiple pushes for one user-visible email,
# and OpenClaw may trigger overlapping hook runs. Without a lock, two runs can read
# the same checkpoint and both notify.
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  flock -x 9
fi

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

run_started_epoch=$(date +%s)

# Priority filter query:
#   1. Primary inbox (exclude promotions/updates/forums)
#   2. label:Missionaries
#   3. label:"SPBC Prayer Chain"
#   4. Voice of the Martyrs (vom.org / persecution.com)
QUERY="is:unread ${time_filter} ((in:inbox AND -category:promotions AND -category:updates AND -category:forums) OR label:Missionaries OR label:\"SPBC Prayer Chain\" OR from:vom.org OR from:persecution.com)"

# Use messages search (not thread search) to get individual emails with body text
result=$(gog gmail messages search "$QUERY" --max "$MAX" --json --include-body --account "$ACCOUNT" 2>/dev/null)

# Check if any messages matched
msg_count=$(echo "$result" | jq -r '.messages | length' 2>/dev/null || echo 0)

if [ -z "$msg_count" ] || [ "$msg_count" -eq 0 ]; then
  # No matches — still update the checkpoint to "now"
  echo "$run_started_epoch" > "$STATE_FILE"
  exit 1
fi

# Truncate body text per message to keep output manageable
result=$(echo "$result" | jq --argjson max "$MAX_BODY" '
  .messages |= [.[] | .body = (.body[:$max] + if (.body | length) > $max then "…[truncated]" else "" end)]
')

# Advance the checkpoint using the max parseable message date (across all matches),
# but never behind the run start. This avoids reprocessing when search order differs.
max_message_epoch=0
while IFS= read -r msg_date; do
  [ -z "$msg_date" ] && continue
  msg_epoch=$(date -d "$msg_date" +%s 2>/dev/null || true)
  if [[ "$msg_epoch" =~ ^[0-9]+$ ]] && [ "$msg_epoch" -gt "$max_message_epoch" ]; then
    max_message_epoch="$msg_epoch"
  fi
done < <(echo "$result" | jq -r '.messages[]?.date // empty')

checkpoint_epoch="$run_started_epoch"
if [ "$max_message_epoch" -gt "$checkpoint_epoch" ]; then
  checkpoint_epoch="$max_message_epoch"
fi
echo "$checkpoint_epoch" > "$STATE_FILE"

echo "$result"
