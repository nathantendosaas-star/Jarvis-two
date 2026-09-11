#!/bin/bash
# pre-tool-context.sh (구 pre-tool-openclaw.sh)
# PreToolUse 훅: 중요 파일 수정 시 additionalContext 자동 주입
# Edit|Write 툴 실행 직전에 Claude에게 관련 주의사항을 전달

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[[ -z "$FILE" ]] && exit 0

CONTEXT=""

# Jarvis 설정 파일
if [[ "$FILE" == *"/.jarvis/config/"*".json" ]] || [[ "$FILE" == *"/.jarvis/config/tasks.json" ]]; then
    CONTEXT="[Jarvis 설정 수정] tasks.json 변경 후 jarvis-cron.sh가 다음 실행 시 자동 반영됨"
fi

# LaunchAgent plist
if [[ "$FILE" == *"Library/LaunchAgents"*".plist" ]]; then
    CONTEXT="[LaunchAgent plist 수정] 변경 후 필수: launchctl unload → 수정 → launchctl load 순서로 재등록"
fi

# Jarvis watchdog/guardian 스크립트
# NOTE: bash 스크립트는 launchd가 매 실행 시 새로 파싱하므로 plist reload 불필요.
# 이전 버전은 watchdog.plist reload를 지시했으나 (1) watchdog.plist는 watchdog.sh 실행 plist로
# guardian과 무관, (2) bash 편집은 다음 크론 주기에 자동 반영되므로 오지시였음.
if [[ "$FILE" == *"watchdog"* ]] || [[ "$FILE" == *"guardian"* ]]; then
    CONTEXT="[자가복구 스크립트 수정] bash 스크립트는 다음 실행 주기에 자동 반영 (reload 불필요). 편집 후 'bash -n <파일>'로 syntax 검증 권장."
fi

# ask-claude.sh (핵심 진입점)
if [[ "$FILE" == *"/.jarvis/bin/ask-claude.sh" ]]; then
    CONTEXT="[ask-claude.sh 수정] 모든 Jarvis 크론/Discord 호출의 핵심 진입점. 변경 후 반드시 테스트: ~/.jarvis/bin/ask-claude.sh test-task '테스트'"
fi

# Claude settings
if [[ "$FILE" == *"/.claude/settings.json" ]]; then
    CONTEXT="[Claude 설정 수정] hooks 변경은 다음 세션부터 적용됨 (현재 세션은 스냅샷 사용)"
fi


# doc-map.json 기반: 코드 파일 편집 시 관련 문서 자동 주입
DOC_MAP="${HOME}/.jarvis/config/doc-map.json"
if [[ -f "$DOC_MAP" && -n "$FILE" ]]; then
    DOC_CONTEXT=$(python3 "${HOME}/.jarvis/state/.pre-tool-docmap.py" "$DOC_MAP" "$FILE" "$(basename "$FILE")" 2>/dev/null)
    if [[ -n "$DOC_CONTEXT" && -z "$CONTEXT" ]]; then
        CONTEXT="$DOC_CONTEXT"
    elif [[ -n "$DOC_CONTEXT" && -n "$CONTEXT" ]]; then
        CONTEXT="${CONTEXT} | ${DOC_CONTEXT}"
    fi
fi

if [[ -n "$CONTEXT" ]]; then
    jq -n --arg ctx "$CONTEXT" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            additionalContext: $ctx
        }
    }'
fi

exit 0
