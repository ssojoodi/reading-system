#!/usr/bin/env bash
set -euo pipefail

# Load environment variables
. .env

cd $BASE_DIR
. ./venv/bin/activate

export run_date=`date +%Y-%m-%d-%H%M%S`
echo "RUN @  ${run_date}" >> $BASE_DIR/logs/run.log
echo "RUN STARTED @  $(date +%H%M%S)" >> $BASE_DIR/logs/run.log

# python read-book.py status
python read-book.py next >> $BASE_DIR/logs/run.log 2>&1

/bin/bash send-daily.sh >> $BASE_DIR/logs/run.log 2>&1
# /bin/bash send-daily.sh --dry-run

echo "RUN ENDED @  $(date +%H%M%S)" >> $BASE_DIR/logs/run.log
