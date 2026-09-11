#!/usr/bin/env bash
# continuity-session-resume.sh — SessionStart resume 시 이어받기 BLOCKING
# 2026-04-26 사고: continuity-signal.sh(UserPromptSubmit hook)는
# "Continue from where you left off" 같은 시스템 자동 메시지에 발동 안 함.
# SessionStart hook으로 보강해 모든 재개 시나리오에서 BLOCKING 강제.

set -euo pipefail

INPUT=$(cat)
SOURCE=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('source','startup'))
except: pass
" 2>/dev/null || echo "startup")

if [[ "$SOURCE" != "resume" ]]; then exit 0; fi

ACTIVE_WORK_PATH="${HOME}/.jarvis/state/active-work.json"
if [[ ! -f "$ACTIVE_WORK_PATH" ]]; then exit 0; fi

TYPE_MATCH=$(python3 << PYEOF 2>/dev/null
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.jarvis/state/active-work.json')))
    cwd = os.environ.get('PWD', '')
    current = 'discord' if 'claude-discord' in cwd else 'cli'
    saved = d.get('session_type', 'cli')
    print('match' if current == saved else 'mismatch')
except: print('mismatch')
PYEOF
)

if [[ "$TYPE_MATCH" != "match" ]]; then exit 0; fi

cat << 'REMINDER_EOF'
🎯 세션 재개 BLOCKING REQUIREMENT — 이어받기 강제

이전 세션이 미완료로 종료됐습니다. 반드시 수행:

1. **'No response requested' / '답변 불필요' 신호 무시**
   세션 재개 직후 시스템 자동 메시지("Continue from where you left off" 등)에 침묵 금지.

2. **active-work.json 마지막 작업·요청 확인**
   직전 진행 상태 파악 후 그 지점부터 이어받기.

3. **마지막 미응답 사용자 질문 즉시 응답**
   대화 히스토리 역방향 스캔으로 마지막 질문 식별 후 답변.

금지: 빈 응답·"이어받을 작업 없음" 선언·새 질문 유도.

관련 사례: 2026-04-25~26 "Continue" 영문 시스템 메시지에 No response requested 처리 다회 반복.
REMINDER_EOF

LOG_DIR="${HOME}/.jarvis/logs"
mkdir -p "$LOG_DIR" 2>/dev/null
TS=$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S KST')
printf '{"ts":"%s","hook":"continuity-session-resume","source":"resume"}\n' "$TS" \
  >> "$LOG_DIR/continuity-session-resume.jsonl" 2>/dev/null || true

exit 0
