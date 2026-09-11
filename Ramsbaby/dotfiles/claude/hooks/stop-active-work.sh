#!/usr/bin/env bash
# stop-active-work.sh — 세션 종료 시 작업 체크포인트 자동 저장
#
# 동작 원리:
#   파일 변경 있음  → active-work.json 갱신 (트랜스크립트에서 컨텍스트 추출)
#   파일 변경 없음  → 기존 체크포인트 유지 (7일 초과 시 자동 삭제)
#
# Stop hook (async: true, timeout: 15)

set -euo pipefail

BOT_HOME="${HOME}/.jarvis"
SESSION_TS="${BOT_HOME}/state/.claude-session-start"
ACTIVE_WORK="${BOT_HOME}/state/active-work.json"
LOG="${BOT_HOME}/logs/active-work.log"

log() { echo "[$(date '+%F %T')] [active-work] $1" >> "$LOG" 2>/dev/null || true; }

INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

SESSION_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(str(d.get('session_id', 'unknown'))[:8])
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")

[[ -f "$SESSION_TS" ]] || { log "No session timestamp — skip"; exit 0; }

SEARCH_DIRS=()
for d in \
    "${BOT_HOME}/lib" "${BOT_HOME}/bin" "${BOT_HOME}/scripts" \
    "${BOT_HOME}/discord" "${BOT_HOME}/config" \
    "${HOME}/.claude/hooks" \
    "${HOME}/jarvis-board/app" "${HOME}/jarvis-board/lib" \
    "${HOME}/jarvis-board/components"; do
    [[ -d "$d" ]] && SEARCH_DIRS+=("$d")
done

changed_raw=""
if [[ ${#SEARCH_DIRS[@]} -gt 0 ]]; then
    changed_raw=$(find "${SEARCH_DIRS[@]}" \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -not -path "*/rag/lancedb/*" \
        -not -path "*/logs/*" \
        -not -path "*/state/active-work.json" \
        -not -path "*/.next/*" \
        \( -name "*.mjs" -o -name "*.js" -o -name "*.sh" \
           -o -name "*.json" -o -name "*.ts" -o -name "*.tsx" \
           -o -name "*.md" -o -name "*.py" \) \
        -newer "$SESSION_TS" 2>/dev/null \
        | sed "s|${HOME}/||" | sort || true)
fi

if [[ -z "$changed_raw" ]]; then
    if [[ -f "$ACTIVE_WORK" ]]; then
        stale=$(python3 -c "
import json
from datetime import datetime, timezone
try:
    d = json.load(open('${ACTIVE_WORK}'))
    updated = datetime.fromisoformat(d.get('updated_at','2000-01-01T00:00:00Z').replace('Z','+00:00'))
    age_days = (datetime.now(timezone.utc) - updated).days
    print('stale' if age_days >= 7 else 'fresh')
except Exception:
    print('stale')
" 2>/dev/null || echo "fresh")
        if [[ "$stale" == "stale" ]]; then
            rm -f "$ACTIVE_WORK"
            log "Cleared stale active-work.json (>7 days)"
        else
            log "No file changes — preserved existing active-work.json"
        fi
    fi
    exit 0
fi

export AW_TRANSCRIPT="$TRANSCRIPT_PATH"
export AW_SESSION_ID="$SESSION_ID"
export AW_OUTPUT="$ACTIVE_WORK"
export AW_FILES="$changed_raw"

python3 - << 'PYEOF'
import json, os
from datetime import datetime, timezone

transcript_path = os.environ.get('AW_TRANSCRIPT', '')
session_id      = os.environ.get('AW_SESSION_ID', 'unknown')
output_path     = os.environ.get('AW_OUTPUT', '')
files_raw       = os.environ.get('AW_FILES', '')

files = [f.strip() for f in files_raw.strip().splitlines() if f.strip()][:20]

last_user = ''
last_asst = ''

if transcript_path and os.path.exists(transcript_path):
    try:
        lines = open(transcript_path, encoding='utf-8', errors='replace').readlines()[-400:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            role    = obj.get('type') or obj.get('role') or ''
            msg     = obj.get('message', obj)
            content = msg.get('content', '')

            if isinstance(content, str):
                text = content.strip()
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    t = block.get('text', '') if block.get('type') == 'text' else ''
                    if t and not t.startswith('<system-reminder') and not t.startswith('[대화 상대]'):
                        parts.append(t)
                text = ' '.join(parts).strip()
            else:
                text = ''

            if not text or len(text) < 5:
                continue

            if role in ('user', 'human') and len(text) < 300:
                last_user = text[:200].replace('\n', ' ').strip()
            elif role in ('assistant', 'ai'):
                last_asst = text[:200].replace('\n', ' ').strip()
    except Exception:
        pass

# Discord 세션 여부 판별 (트랜스크립트 경로 기준)
session_type = 'discord' if 'claude-discord' in transcript_path else 'cli'

data = {
    "updated_at":        datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "session_id":        session_id,
    "session_type":      session_type,
    "modified_files":    files,
    "last_user_request": last_user,
    "last_work_summary": last_asst,
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"[active-work] saved: {len(files)} files, session={session_id}")
PYEOF

log "Saved: $(echo "$changed_raw" | wc -l | tr -d ' ') files changed, session:${SESSION_ID}"
exit 0
