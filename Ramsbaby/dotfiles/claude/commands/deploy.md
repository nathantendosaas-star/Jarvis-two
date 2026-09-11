---
description: "Jarvis 배포 및 업데이트. git pull, smoke test, 봇 재시작 등 안전한 배포 수행. '배포해줘', '업데이트 진행', 'deploy', '최신화' 요청 시 사용."
---

# Jarvis 배포/업데이트

Jarvis AI 시스템을 안전하게 업데이트합니다.

## 배포 전 체크리스트
1. 현재 시스템 상태 확인 (`/doctor`)
2. 변경된 파일 확인
3. Discord bot 활성 세션 없는지 확인

## 배포 단계

### LaunchAgent 업데이트
```bash
launchctl unload ~/Library/LaunchAgents/ai.jarvis.discord-bot.plist
# ... 파일 수정 ...
launchctl load ~/Library/LaunchAgents/ai.jarvis.discord-bot.plist
```

### 크론 업데이트
```bash
crontab -e
# 변경 후 즉시 적용됨
```

### tasks.json 업데이트
```bash
# ~/.jarvis/config/tasks.json 수정
# jarvis-cron.sh가 다음 실행 시 자동 반영
```

### 검증
```bash
# Discord bot 재시작 확인
launchctl list | grep jarvis
tail -5 ~/.jarvis/logs/watchdog.log

# 크론 테스트
~/.jarvis/bin/jarvis-cron.sh system-health

# E2E
~/.jarvis/scripts/e2e-test.sh
```
