#!/usr/bin/env bash
INPUT=$(cat)
DIR=$(echo "$INPUT" | jq -r '.workspace.current_dir // .cwd // "."')
MODEL=$(echo "$INPUT" | jq -r '.model.display_name // "unknown"')
COST=$(echo "$INPUT" | jq -r '.cost.total_cost_usd // 0')
ADD=$(echo "$INPUT" | jq -r '.cost.total_lines_added // 0')
DEL=$(echo "$INPUT" | jq -r '.cost.total_lines_removed // 0')
BRANCH=$(git -C "$DIR" branch --show-current 2>/dev/null || echo "—")
printf '%s | %s | $%.4f | +%s -%s' "$MODEL" "$BRANCH" "$COST" "$ADD" "$DEL"
