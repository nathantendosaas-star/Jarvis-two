#!/usr/bin/env bash
# stop-rag-sync.sh — Claude Code 세션 종료 시 Jarvis RAG 자동 재인덱싱
# ~/.jarvis/ 파일이 변경됐을 때만 실행 (불필요한 OpenAI API 호출 방지)

BOT_HOME="${HOME}/.jarvis"
STATE_FILE="${BOT_HOME}/rag/index-state.json"
RAG_INDEXER="${BOT_HOME}/bin/rag-index.mjs"
LOG="${BOT_HOME}/logs/rag-sync.log"

# rag-index.mjs 없으면 조용히 종료
[[ -f "$RAG_INDEXER" ]] || exit 0

# STATE_FILE 없으면 항상 재인덱싱 (첫 실행 케이스)
if [[ ! -f "$STATE_FILE" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] RAG sync triggered: no state file yet" >> "$LOG"
  nohup timeout 2700 bash "${BOT_HOME}/bin/rag-index-safe.sh" >> "$LOG" 2>&1 &
  exit 0
fi

# ~/.jarvis/ 에서 state file 이후 변경된 .md .mjs .js .sh 파일 있는지 확인
changed=$(find "$BOT_HOME" \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -path "*/rag/lancedb/*" \
  -not -path "*/logs/*" \
  \( -name "*.md" -o -name "*.mjs" -o -name "*.js" -o -name "*.sh" \) \
  -newer "$STATE_FILE" 2>/dev/null | head -1)

if [[ -z "$changed" ]]; then
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] RAG sync triggered by: $changed" >> "$LOG"

# 백그라운드로 실행 (세션 종료 지연 방지) — rag-index-safe.sh로 OMP 강제
nohup timeout 2700 bash "${BOT_HOME}/bin/rag-index-safe.sh" >> "$LOG" 2>&1 &

exit 0
