---
description: "서비스 전체 상태 대시보드. 크론, 봇, LaunchAgent, 모니터링 등 전체 현황 조회. '서비스 상태', '대시보드', '전체 현황', '다 돌아가나?', '서비스 확인' 요청 시 사용."
---

# 서비스 전체 상태 대시보드

Jarvis AI 시스템 전체 서비스 상태를 한눈에 보여주세요.

## 점검 항목 (모두 실행)

### 1. LaunchAgent 상태
```bash
launchctl list | grep -E "jarvis|glances"
```

### 2. Jarvis 핵심 서비스
```bash
# Discord bot 프로세스
ps aux | grep "discord-bot.js" | grep -v grep

# Watchdog 최근 로그
tail -3 ~/.jarvis/logs/watchdog.log

# 헬스 상태
cat ~/.jarvis/state/health.json
```

### 3. 시스템 리소스
```bash
vm_stat | head -5
df -h / | tail -1
uptime
```

### 4. 크론 상태
```bash
# 최근 실행 결과
tail -20 ~/.jarvis/logs/cron.log | grep -E "START|DONE|FAIL"
# 활성 크론 수
crontab -l | grep -v "^#" | grep -c jarvis
```

### 5. RAG 인덱서
```bash
tail -3 ~/.jarvis/logs/rag-index.log
```

### 6. 알림 시스템
```bash
# ntfy 토픽
jq -r '.ntfy.topic' ~/.jarvis/config/monitoring.json 2>/dev/null || echo "설정 확인 필요"
# Discord Webhook
jq -r '.discord.webhook_url' ~/.jarvis/config/monitoring.json 2>/dev/null | head -c 60
```

### 7. Glances 웹 대시보드
```bash
curl -s --max-time 2 http://localhost:61208/api/4/cpu | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'CPU: {d[\"total\"]}%')" 2>/dev/null || echo "Glances 응답 없음"
```

## 출력 형식
```
📊 Jarvis Status Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ LaunchAgents
  ai.jarvis.discord-bot   ✅ PID xxxxx
  ai.jarvis.watchdog      ✅ loaded (interval)
  ai.openclaw.glances     ✅ PID xxxxx (61208)

🤖 Jarvis 코어
  Discord bot    ✅ running (XMB)
  Watchdog       ✅ last: healthy
  RAG indexer    ✅ XXXX chunks, XXX sources

🖥️ System
  CPU: X% | RAM: X/16GB | Disk: X%
  Uptime: X days

⏰ 크론: X개 active
  최근: [task] SUCCESS/FAIL

🔔 알림
  Discord webhook  ✅
  ntfy             ✅ openclaw-f101e56cb98a
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

문제 항목은 ❌로 표시하고 복구 방법 안내.
