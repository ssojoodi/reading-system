#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./send-daily.sh [--dry-run]

Sends the most recent *.html file from output_files/ as a rich-text (HTML)
email body via Mailgun API. Recipients are read from .env (RECIPIENTS, comma-separated).

Requires: MAILGUN_API_KEY, MAILGUN_DOMAIN, RECIPIENTS (in .env).
Optional: MAILGUN_FROM (default: Sahand Sojoodi <sahand@sojoodi.com>).

Options:
  --dry-run          Print what would be sent, do not send
  -h, --help         Show this help
USAGE
}

DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    *)
      echo "Error: unexpected argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

# Load environment variables
. .env

require_var() {
  local name="$1"
  [[ -n "${!name:-}" ]] && return 0
  echo "Error: $name is not set in .env" >&2
  exit 1
}

# Validate environment variables
require_var RECIPIENTS
require_var MAILGUN_API_KEY
require_var MAILGUN_DOMAIN
require_var MAILGUN_FROM

IFS=$', \t' read -ra RECIPIENTS <<< "${RECIPIENTS}"

LATEST_HTML="$(ls -1t -- output_files/*.html 2>/dev/null | head -n 1)"
[[ -z "$LATEST_HTML" || ! -f "$LATEST_HTML" ]] && { echo "Error: no .html files in output_files" >&2; exit 1; }

TITLE="$(sed -n 's/.*<h1>\([^<]*\)<\/h1>.*/\1/p' "$LATEST_HTML" | head -n 1)"
PCT="$(grep -oE '[0-9]{1,3}% complete' "$LATEST_HTML" | head -n 1 | cut -d' ' -f1)"
if [[ -z "$TITLE" ]]; then
  TITLE="$(basename "$LATEST_HTML" .html)"
fi
if [[ -n "$PCT" ]]; then
  SUBJECT="Daily Reading: $TITLE ($PCT)"
else
  SUBJECT="Daily Reading: $TITLE"
fi

if [[ "$DRY_RUN" == "true" ]]; then
  TO_HEADER=$(IFS=,; echo "${RECIPIENTS[*]}")
  echo "Dry run: would send $LATEST_HTML to $TO_HEADER (subject: $SUBJECT)"
  exit 0
fi

CURL_BCC_ARGS=()
for r in "${RECIPIENTS[@]}"; do
  CURL_BCC_ARGS+=(-F "bcc=$r")
done

# To: is required by Mailgun; use From so all real recipients are in BCC only
curl -s --user "api:${MAILGUN_API_KEY}" \
  "https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages" \
  -F "from=${MAILGUN_FROM}" \
  -F "to=${MAILGUN_FROM}" \
  "${CURL_BCC_ARGS[@]}" \
  -F "subject=${SUBJECT}" \
  -F "html=@${LATEST_HTML}" \
  || { echo "Error: Mailgun API request failed" >&2; exit 1; }

echo "Sent $LATEST_HTML to ${RECIPIENTS[*]}"
