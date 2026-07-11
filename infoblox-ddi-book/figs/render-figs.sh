#!/usr/bin/env bash
# Render every infoblox-ddi-book/**/figs/*.mmd to a same-named .png using the shared
# AAN house-style theme and the preinstalled Chromium. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"          # infoblox-ddi-book/
THEME="$ROOT/figs/mermaid-theme.json"
CHROME="$(ls /opt/pw-browsers/chromium*/chrome-linux/chrome 2>/dev/null | head -1)"
PC="$(mktemp)"; printf '{"executablePath":"%s","args":["--no-sandbox","--disable-gpu"]}' "$CHROME" > "$PC"
count=0
while IFS= read -r -d '' mmd; do
  png="${mmd%.mmd}.png"
  npx -y @mermaid-js/mermaid-cli -i "$mmd" -o "$png" -c "$THEME" -p "$PC" -b transparent -s 2 >/dev/null 2>&1
  echo "rendered $(basename "$png")"; count=$((count+1))
done < <(find "$ROOT" -path '*/figs/*.mmd' -print0)
echo "TOTAL: $count figures"
