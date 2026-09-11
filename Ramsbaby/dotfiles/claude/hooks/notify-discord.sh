#!/bin/bash
# Notification hook: 권한 요청이나 idle 상태를 macOS 알림으로 전달
INPUT=$(cat)
TYPE=$(echo "$INPUT" | jq -r '.notification_type // empty')
MESSAGE=$(echo "$INPUT" | jq -r '.message // empty')

case "$TYPE" in
  permission_prompt)
    osascript -e "display notification \"${MESSAGE}\" with title \"Claude Code\" subtitle \"권한 요청\"" 2>/dev/null
    ;;
  idle_prompt)
    osascript -e "display notification \"${MESSAGE}\" with title \"Claude Code\" subtitle \"작업 완료\"" 2>/dev/null
    ;;
esac

exit 0
