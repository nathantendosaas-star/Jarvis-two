#!/usr/bin/env bash
# sensor-skill-trigger.sh — 스킬 트리거 키워드 자동 감지 hook
#
# 주인님 발화에서 "검증해줘" / "리뷰" / "회고" 같은 트리거 키워드 감지 시
# assistant context에 system-reminder로 해당 스킬 invoke 요구를 주입.
# Iron Law 6 (Verify Before Declare) + jarvis-ethos.md "스킬 트리거 키워드 BLOCKING"
# 구조적 방어 — self-review 편향으로 인한 실결함 누락 사고 재발 방지.
#
# 2026-04-22 14:37 KST 사고: RAG 복구 후 "검증해줘" → /verify 스킵 → 자체 bash 검증
# → PASS 자가선언. 독립 감사관 Agent가 4개 실결함 적발. 이 hook이 있었다면 차단.

set -euo pipefail

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    p = d.get('prompt') or d.get('user_prompt') or ''
    print(p[:2000].lower())
except Exception:
    pass
" 2>/dev/null || echo "")

if [[ -z "$PROMPT" ]]; then exit 0; fi

# ─── 트리거 매트릭스 (ethos.md 와 SSoT; bash 3.2 호환 case 분기) ───
MATCHED=""
if echo "$PROMPT" | grep -qE "검증해줘|재검증|제대로 됐어|프로덕션 통과|verify해줘|/verify|검증스킬"; then
  MATCHED="verify"
elif echo "$PROMPT" | grep -qE "리뷰해줘|리뷰 해줘|코드 검토|/review"; then
  MATCHED="review"
elif echo "$PROMPT" | grep -qE "회고|회고록|/retro|작업 정리해줘"; then
  MATCHED="retro"
elif echo "$PROMPT" | grep -qE "디버깅|근본 원인|근본원인|왜 실패|investigate|/investigate"; then
  MATCHED="investigate"
elif echo "$PROMPT" | grep -qE "뭐 문제 없|건강 체크|건강체크|시스템 점검|/doctor"; then
  MATCHED="doctor"
elif echo "$PROMPT" | grep -qE "긴급 상황|장애 대응|봇이 죽었|/crisis"; then
  MATCHED="crisis"
fi

if [[ -z "$MATCHED" ]]; then exit 0; fi

# 이미 같은 턴에 /skill 형태로 호출 중이면 skip (중복 reminder 방지)
if echo "$PROMPT" | grep -qE "^/${MATCHED}( |$)"; then
  exit 0
fi

# system-reminder 주입 — stdout이 assistant context에 append됨
cat << EOF
🎯 스킬 트리거 감지: /$MATCHED

주인님 발화에서 \`/$MATCHED\` 트리거 키워드가 감지되었습니다.

**BLOCKING REQUIREMENT (jarvis-ethos.md)**: 다른 도구 호출 전에 반드시 Skill tool로
\`/$MATCHED\` 를 먼저 invoke하십시오. 자체 bash 검증·직접 재확인·"이 정도면 충분"
자기합리화는 금지입니다.

사고 사례: 2026-04-22 14:37 KST — RAG 복구 후 "검증해줘" 요청에서 /verify 스킵,
자체 bash 6개 체크로 PASS 자가선언 → 독립 감사관 Agent가 4개 실결함(du 범위 오류·
서킷브레이커 관측 부재·git 미커밋·디스크 91%) 적발. Self-review 편향 실증.

관련 룰: ~/.claude/rules/jarvis-ethos.md "스킬 트리거 키워드 BLOCKING REQUIREMENT"
EOF

# 관측 로그 (audit trail)
LOG_DIR="${HOME}/.jarvis/logs"
mkdir -p "$LOG_DIR"
TS=$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S KST')
SAFE_PROMPT=$(python3 -c "import sys,json; print(json.dumps(sys.argv[1][:200]))" "$PROMPT" 2>/dev/null || echo '""')
printf '{"ts":"%s","skill":"%s","prompt":%s}\n' "$TS" "$MATCHED" "$SAFE_PROMPT" \
  >> "$LOG_DIR/skill-trigger.jsonl" 2>/dev/null || true

exit 0
