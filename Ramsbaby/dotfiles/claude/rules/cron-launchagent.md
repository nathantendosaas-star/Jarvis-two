---
paths:
  - "**/*.plist"
  - "**/crontab*"
  - "**/*launchd*"
  - "**/LaunchAgents/**"
---

# Cron & LaunchAgent 규칙

## 핵심 원칙 (SSoT) — 2026-04-15 Nexus 정책 반영

| 용도 | 도구 | 이유 |
|------|------|------|
| **주기적 LLM/스크립트 태스크** | **Nexus (tasks.json)** | 정책 SSoT, budget/retry/audit 통합 |
| 직접 shell 크론 (Nexus 비경유) | Crontab 직접 | 레거시만, 신규는 tasks.json 우선 |
| KeepAlive 데몬 (죽으면 즉시 재시작) | **LaunchAgent** | OS 레벨 자동 재시작 필요 |

> "Nexus는 뇌, crontab은 디스패처, LaunchAgent는 경비원" — 태스크 등록은 Nexus, 주기 발화는 5개 crontab 엔트리가 jarvis-cron.sh 통해 dispatch, 상시 유지는 LaunchAgent.

## 신규 주기 태스크 등록 흐름 (필수)

```
1. ~/.jarvis/config/tasks.json 에 엔트리 추가
   (schema: ~/.jarvis/config/tasks.schema.json 참고)
2. node ~/.jarvis/scripts/gen-tasks-index.mjs 실행
   → effective-tasks.json 재생성 + TASKS-INDEX.md 갱신
3. 끝. crontab 추가 불필요 — 기존 5개 엔트리가 jarvis-cron.sh로 dispatch.
```

- **LaunchAgent plist 신규 생성 금지** (주기 태스크용 아님)
- **crontab 직접 등록 금지** (tasks-integrity-audit 사각지대)
- 위반 시 `policy_duplicate` 또는 `policy_orphan_plist` 경보 발생

## 금지 사항

```xml
<!-- 금지: LaunchAgent에 스케줄 인터벌 사용 -->
<key>StartCalendarInterval</key>  <!-- 절대 신규 추가 금지 -->
<key>StartInterval</key>          <!-- 절대 신규 추가 금지 -->
```

- **신규 스케줄 태스크는 무조건 crontab에만 등록**
- LaunchAgent에 `StartCalendarInterval` / `StartInterval` 신규 생성 금지
- 위반 시 DUPLICATE 발생 → audit 실패

## LaunchAgent plist 명명 규칙

```
ai.jarvis.[서비스명]
```

예시:
- `ai.jarvis.discord-bot.plist`
- `ai.jarvis.rag-watcher.plist`
- `ai.jarvis.dashboard.plist`

## KeepAlive 데몬 목록 (현재 운영 중)

```
ai.jarvis.discord-bot        — Discord 봇
ai.jarvis.watchdog           — 봇 감시 + stale claude -p 정리
ai.jarvis.rag-watcher        — RAG 파일 변경 감지 → 큐 기록
ai.jarvis.dashboard          — Jarvis Board 서버
ai.jarvis.dashboard-tunnel   — Board 터널
ai.jarvis.orchestrator       — 이벤트 오케스트레이터
ai.jarvis.event-watcher      — 이벤트 감시
ai.jarvis.webhook-listener   — 웹훅 수신
```

별도 관리:
- `actions.runner.Ramsbaby-jarvis-board.mac-mini-macmini` — GitHub Actions Runner (직접 편집 금지)

## KeepAlive plist 최소 템플릿

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.jarvis.[서비스명]</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/script.sh</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/<YOUR_USERNAME>/.jarvis/logs/[서비스명].log</string>
    <key>StandardErrorPath</key>
    <string>/Users/<YOUR_USERNAME>/.jarvis/logs/[서비스명].err.log</string>
</dict>
</plist>
```

## Guardian (자동 복구)

`launchd-guardian.sh`가 **매 3분** cron으로 실행.

- discord-bot / watchdog 언로드 감지 → 자동 `launchctl load` 재등록
- 로그: `~/.jarvis/logs/launchd-guardian.log`

```
*/3 * * * * /path/to/launchd-guardian.sh
```

Guardian이 있으므로 KeepAlive 데몬이 실수로 언로드되어도 3분 내 자동 복구됨.

## 감사 (Audit)

```bash
# DUPLICATE 0건 유지 필수
~/.jarvis/scripts/audit-la-cron-dry.sh
```

- LA(LaunchAgent)와 crontab 간 중복 스케줄 교차 비교
- `DUPLICATE` 항목이 1건이라도 있으면 즉시 정리
- plist 수정 / crontab 추가 후 반드시 실행

## crontab 등록 패턴

```bash
# 안전한 crontab 편집
crontab -l > /tmp/crontab.bak   # 백업
crontab -e                       # 편집

# 주요 스케줄 예시
*/3 * * * *  /path/launchd-guardian.sh          # LA 감시
*/5 * * * *  /path/bot-watchdog.sh              # 봇 로그 freshness
1,31 * * * * /path/system-health.sh             # 시스템 상태
15 6 * * *   /path/morning-standup.sh           # 모닝 브리핑
0 3 * * 0    /path/server_maintenance.sh        # 주간 정비
```
