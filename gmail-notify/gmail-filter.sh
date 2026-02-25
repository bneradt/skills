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
SEEN_MAX="${GMAIL_FILTER_SEEN_MAX:-500}"
STATE_DIR="${HOME}/.openclaw/state/gmail-filter"
STATE_FILE="${STATE_DIR}/last-check-epoch"
LOCK_FILE="${STATE_DIR}/lock"
SEEN_FILE="${STATE_DIR}/seen-signatures.txt"

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

# Allow-listed sender domains and labels for priority mail.
ALLOWLIST_FROM_DOMAINS=(
  "vomusa.org"
  "churchcenteronline.com"
)

ALLOWLIST_LABELS=(
  "Missionaries"
  "SPBC Prayer Chain"
)

from_clauses=()
for domain in "${ALLOWLIST_FROM_DOMAINS[@]}"; do
  from_clauses+=("from:${domain}")
done

label_clauses=()
for label in "${ALLOWLIST_LABELS[@]}"; do
  label_clauses+=("label:\"${label}\"")
done

from_query=""
if [ "${#from_clauses[@]}" -gt 0 ]; then
  from_query="$(printf ' OR %s' "${from_clauses[@]}")"
  from_query="${from_query# OR }"
fi

label_query=""
if [ "${#label_clauses[@]}" -gt 0 ]; then
  label_query="$(printf ' OR %s' "${label_clauses[@]}")"
  label_query="${label_query# OR }"
fi

priority_groups=(
  "(in:inbox AND -category:promotions AND -category:updates AND -category:forums)"
)
[ -n "$label_query" ] && priority_groups+=("$label_query")
[ -n "$from_query" ] && priority_groups+=("$from_query")

priority_query="$(printf ' OR %s' "${priority_groups[@]}")"
priority_query="${priority_query# OR }"

# Priority filter query:
#   1. Primary inbox (exclude promotions/updates/forums)
#   2. Allow-listed labels (see ALLOWLIST_LABELS)
#   3. Allow-listed sender domains (see ALLOWLIST_FROM_DOMAINS)
QUERY="is:unread ${time_filter} (${priority_query})"

# Use messages search (not thread search) to get individual emails with body text
result=$(gog gmail messages search "$QUERY" --max "$MAX" --json --include-body --account "$ACCOUNT" 2>/dev/null)
raw_result="$result"

# De-duplicate by stable message signature (prefer Gmail ids/thread ids; fall back
# to from+subject+date) to suppress repeated Gmail push events for the same email.
if [ -s "$SEEN_FILE" ]; then
  seen_json=$(jq -Rsc 'split("\n") | map(select(length > 0))' "$SEEN_FILE" 2>/dev/null || echo '[]')
else
  seen_json='[]'
fi
[ -n "$seen_json" ] || seen_json='[]'
result=$(echo "$raw_result" | jq --argjson seen "$seen_json" '
  .messages |= map(
    . as $m
    | (($m.id // $m.messageId // $m.threadId // (($m.from // "") + "|" + ($m.subject // "") + "|" + ($m.date // ""))) | tostring) as $sig
    | select(($sig | length) == 0 or (($seen | index($sig)) | not))
  )
')

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

# Record signatures from all fetched messages (including duplicates) so later
# repeated push events are suppressed quickly.
new_signatures=$(echo "$raw_result" | jq -r '
  .messages[]? |
  ((.id // .messageId // .threadId // ((.from // "") + "|" + (.subject // "") + "|" + (.date // ""))) | tostring)
  | select(length > 0)
')
if [ -n "$new_signatures" ]; then
  {
    cat "$SEEN_FILE" 2>/dev/null || true
    printf '%s\n' "$new_signatures"
  } | tail -n "$SEEN_MAX" > "${SEEN_FILE}.tmp"
  mv "${SEEN_FILE}.tmp" "$SEEN_FILE"
fi

# Advance the checkpoint using the max parseable message date (across all matches),
# but never behind the run start. This avoids reprocessing when search order differs.
max_message_epoch=0
while IFS= read -r msg_date; do
  [ -z "$msg_date" ] && continue
  msg_epoch=$(date -d "$msg_date" +%s 2>/dev/null || true)
  if [[ "$msg_epoch" =~ ^[0-9]+$ ]] && [ "$msg_epoch" -gt "$max_message_epoch" ]; then
    max_message_epoch="$msg_epoch"
  fi
done < <(echo "$raw_result" | jq -r '.messages[]?.date // empty')

checkpoint_epoch="$run_started_epoch"
if [ "$max_message_epoch" -gt "$checkpoint_epoch" ]; then
  checkpoint_epoch="$max_message_epoch"
fi
echo "$checkpoint_epoch" > "$STATE_FILE"

echo "$result"
