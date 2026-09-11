#!/usr/bin/env bash
# post-compact-save.sh — PostCompact 훅: 컴팩션 요약을 파일로 저장
# RAG 인덱서가 docs/를 감시하므로 다음 Stop 훅 때 자동 인덱싱됨
# async, timeout 10s

set -euo pipefail

INPUT=$(cat)
TRIGGER=$(echo "$INPUT" | jq -r '.trigger // "unknown"')
SUMMARY=$(echo "$INPUT" | jq -r '.compact_summary // ""')
SESSION=$(echo "$INPUT" | jq -r '.session_id // "unknown"' | cut -c1-8)

[ -z "$SUMMARY" ] && exit 0

BOT_HOME="${HOME}/.jarvis"
COMPACT_LOG="${BOT_HOME}/docs/compact-summaries.md"
LOG="${BOT_HOME}/logs/post-compact.log"

mkdir -p "$(dirname "$COMPACT_LOG")" 2>/dev/null || true

NOW=$(date '+%Y-%m-%d %H:%M')

# compact-summaries.md 에 prepend (최근 10개 유지)
{
  echo "## ${NOW} [${TRIGGER}] session:${SESSION}"
  echo ""
  echo "$SUMMARY"
  echo ""
  echo "---"
  echo ""
  # 기존 내용 — 헤더(##) 기준 최근 9개만 유지
  if [ -f "$COMPACT_LOG" ]; then
    python3 - "$COMPACT_LOG" <<'PY'
import sys, re
content = open(sys.argv[1]).read()
blocks = re.split(r'(?=^## \d{4})', content, flags=re.MULTILINE)
kept = [b for b in blocks if b.strip()][:9]
print(''.join(kept), end='')
PY
  fi
} > "${COMPACT_LOG}.tmp" && mv "${COMPACT_LOG}.tmp" "$COMPACT_LOG"

echo "[$(date '+%F %T')] PostCompact saved (${TRIGGER}, session:${SESSION})" >> "$LOG"
exit 0
