#!/usr/bin/env bash
# stop-session-save.sh — Claude Code 세션 종료 시 대화 내용을 마크다운으로 저장
# context-extractor.mjs가 다음 날 새벽에 이 파일을 읽어 도메인별로 분류함
# Stop hook (async)

set -euo pipefail

INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null || true)
CWD=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null || true)

SESSIONS_DIR="${HOME}/.jarvis/context/claude-code-sessions"
LOG="${HOME}/.jarvis/logs/session-save.log"

log() { echo "[$(date '+%F %T')] [session-save] $1" >> "$LOG" 2>/dev/null || true; }

# 디버그: transcript_path 상태 기록
log "INPUT: transcript_path=${TRANSCRIPT_PATH:-EMPTY} cwd=${CWD:-EMPTY}"
if [[ -n "$TRANSCRIPT_PATH" ]]; then
  log "  transcript exists: $(test -f "$TRANSCRIPT_PATH" && echo YES || echo NO)"
  [[ -f "$TRANSCRIPT_PATH" ]] && log "  transcript size: $(wc -c < "$TRANSCRIPT_PATH" | tr -d ' ') bytes"
fi

[[ -z "$TRANSCRIPT_PATH" || ! -f "$TRANSCRIPT_PATH" ]] && { log "SKIP: transcript 없음"; exit 0; }

# 프로젝트명 (cwd 기반)
PROJECT=$(basename "${CWD:-unknown}" | tr ' ' '-' | tr '/' '-')
[[ -z "$PROJECT" || "$PROJECT" == "-" ]] && PROJECT="unknown"

mkdir -p "${SESSIONS_DIR}/${PROJECT}"

TS=$(date '+%Y-%m-%d-%H%M%S')
OUT="${SESSIONS_DIR}/${PROJECT}/${TS}.md"

# JSONL → 마크다운 변환 (human/assistant 텍스트만, tool use 제외)
python3 - "$TRANSCRIPT_PATH" "$OUT" "$CWD" << 'PYEOF'
import sys, json

transcript_path, out_path, cwd = sys.argv[1], sys.argv[2], sys.argv[3]

messages = []
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 최신 포맷: {type: 'user'|'assistant', message: {role, content: [...]}}
            # 구 포맷 호환: {role: 'user'|'assistant'|'human', content: [...] or str}
            role = obj.get('role', '')
            msg_type = obj.get('type', '')
            message = obj.get('message') if isinstance(obj.get('message'), dict) else None

            # 유효 role 결정 (신 포맷 우선, 구 포맷 fallback)
            if message and message.get('role'):
                eff_role = message.get('role')
            elif msg_type in ('user', 'assistant', 'human'):
                eff_role = 'user' if msg_type == 'human' else msg_type
            elif role in ('user', 'assistant', 'human'):
                eff_role = 'user' if role == 'human' else role
            else:
                continue  # 메타 레코드(queue-operation/attachment/last-prompt 등) 스킵

            # 유효 content 결정 (신 포맷: message.content / 구 포맷: obj.content)
            content = message.get('content') if message else obj.get('content', '')

            if isinstance(content, list):
                text = ' '.join(
                    c.get('text', '') for c in content
                    if isinstance(c, dict) and c.get('type') == 'text'
                )
            elif isinstance(content, str):
                text = content
            else:
                continue
            text = text.strip()
            if text and len(text) > 10 and eff_role in ('user', 'assistant'):
                messages.append((eff_role, text))

except Exception as e:
    sys.exit(0)

if len(messages) < 2:
    sys.exit(0)

from datetime import datetime
date_str = datetime.now().strftime('%Y-%m-%d %H:%M KST')

lines = [f"# Claude Code 세션 — {date_str}", f"\n> 프로젝트: {cwd}\n"]
for role, text in messages:
    prefix = "**사용자**" if role == 'user' else "**Claude**"
    # 너무 긴 메시지는 앞부분만 (RAG 인덱싱 효율)
    truncated = text[:2000] + ('...(생략)' if len(text) > 2000 else '')
    lines.append(f"\n{prefix}: {truncated}")

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"saved: {out_path} ({len(messages)} messages)")
PYEOF

# 저장 후 파일 존재 확인
if [[ -f "$OUT" ]]; then
  SIZE=$(wc -c < "$OUT" | tr -d ' ')
  log "저장 완료: ${OUT} (${SIZE} bytes)"
else
  log "저장 실패! 파일 없음: ${OUT}"
  log "  transcript_path: ${TRANSCRIPT_PATH}"
  log "  cwd: ${CWD}"
  log "  PROJECT: ${PROJECT}"
fi
exit 0
