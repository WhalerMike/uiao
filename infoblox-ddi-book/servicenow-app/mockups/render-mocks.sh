#!/usr/bin/env bash
# Render the illustrative ServiceNow-style UI mock HTML files to PNG using the
# preinstalled Chromium at 2x scale. Heights are tuned per screen to fit content.
# Idempotent — re-run after editing any .html or sn-mock.css.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME="$(ls /opt/pw-browsers/chromium*/chrome-linux/chrome 2>/dev/null | head -1)"
shoot(){ # <file-stem> <height>
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --screenshot="$DIR/$1.png" \
    --window-size="1200,$2" "file://$DIR/$1.html" >/dev/null 2>&1
  echo "rendered $1.png (1200x$2 @2x)"
}
shoot sn-01-catalog-request 1330
shoot sn-02-approval 900
shoot sn-03-request-status 930
shoot sn-04-flow-designer 1190
shoot sn-05-cmdb-ci 760
echo "DONE."
