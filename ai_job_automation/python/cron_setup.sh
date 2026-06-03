#!/usr/bin/env bash
# Installs a daily cron job that runs the automation at 8:00 AM local time.
# Usage: bash cron_setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
LOG="$SCRIPT_DIR/job_automation.log"
CRON_LINE="0 8 * * *  cd \"$SCRIPT_DIR\" && \"$PYTHON\" main.py >> \"$LOG\" 2>&1"

# Remove any previous entry for this script, then add the new one
( crontab -l 2>/dev/null | grep -v "ai_job_automation.*main.py" || true
  echo "$CRON_LINE"
) | crontab -

echo "Cron job installed successfully."
echo ""
echo "  Schedule : every day at 08:00 AM (local time)"
echo "  Command  : $PYTHON $SCRIPT_DIR/main.py"
echo "  Log      : $LOG"
echo ""
echo "Verify with:   crontab -l"
echo "Remove with:   crontab -e  (delete the line)"
