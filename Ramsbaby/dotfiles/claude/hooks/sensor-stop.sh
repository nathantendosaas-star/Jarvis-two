#!/usr/bin/env bash
# sensor-stop.sh — Phase 0 Sensor (Claude Code CLI)
# Stop 훅: 턴 종료 시 response-ledger.jsonl에 append + last-trace 갱신
# Discord 봇의 response-ledger 쓰기와 동일 스키마 (source 태그로 구분).
#
# 입력 JSON: { session_id, transcript_path, cwd, hook_event_name, stop_hook_active }

set -euo pipefail

STATE_DIR="${HOME}/.jarvis/state"
mkdir -p "$STATE_DIR"

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('session_id', ''))
except Exception:
    pass
" 2>/dev/null || echo "")

CWD=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('cwd', ''))
except Exception:
    pass
" 2>/dev/null || echo "")

TRANSCRIPT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('transcript_path', ''))
except Exception:
    pass
" 2>/dev/null || echo "")

if [[ -z "$SESSION_ID" ]]; then exit 0; fi

# transcript에서 마지막 턴의 tool 사용 개수 대충 추산 (best-effort, 실패해도 OK)
TOOL_COUNT=0
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
  TOOL_COUNT=$(tail -100 "$TRANSCRIPT" 2>/dev/null | python3 -c "
import json, sys
count = 0
for line in sys.stdin:
    try:
        d = json.loads(line)
        # assistant message with tool_use blocks
        msg = d.get('message', {})
        content = msg.get('content', [])
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'tool_use':
                    count += 1
    except Exception:
        continue
print(count)
" 2>/dev/null || echo "0")
fi

TRACE_ID="cli-${SESSION_ID}-$(date +%s%N | cut -c1-13)"
TS=$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')
SAFE_CWD=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$CWD" 2>/dev/null || echo '""')

printf '{"ts":"%s","source":"claude-code-cli","traceId":"%s","sessionId":"%s","cwd":%s,"toolCount":%s}\n' \
  "$TS" "$TRACE_ID" "$SESSION_ID" "$SAFE_CWD" "$TOOL_COUNT" \
  >> "$STATE_DIR/response-ledger.jsonl" 2>/dev/null || true

# 다음 UserPromptSubmit에서 피드백 오면 이 trace에 score 부여용
echo "$TRACE_ID" > "/tmp/claude-sensor-last-trace-${SESSION_ID}" 2>/dev/null || true

exit 0
