---
description: "스탠드업 리포트. 어제 한 일, 오늘 할 일 자동 정리. '스탠드업', '어제 뭐 했지', '오늘 할 일', '일일 보고' 요청 시 사용."
---

# 스탠드업 리포트

어제 한 일과 오늘 할 일을 자동으로 정리해주세요.

## 데이터 소스

### 1. 어제 한 일
- `git log --since="yesterday 00:00" --until="today 00:00" --oneline --all` (~/openclaw 기준)
- `~/openclaw/logs/auto-retry.jsonl`에서 어제 실행 요약
- 어제 완료된 GitHub 이슈/PR 확인 (gh 명령어)

### 2. 오늘 할 일
- `gog tasks list "MDE3MjE5NzU0MjA3NTAxOTg4ODc6MDow" --account ${GOOGLE_ACCOUNT}`에서 미완료 할 일
- `gog calendar list --from today --to today --account ${GOOGLE_ACCOUNT}`에서 오늘 일정
- 열린 GitHub 이슈 중 우선순위 높은 것

### 3. 블로커
- auto-retry 실패 패턴이 있으면 표시
- 시스템 이상 징후가 있으면 표시

## 출력 형식
```
📋 Stand-up Report - YYYY-MM-DD (요일)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 어제 한 일
  • [커밋/작업 요약1]
  • [커밋/작업 요약2]
  • 시스템: XX회 실행, 성공률 XX%

📌 오늘 할 일
  • [ ] 할 일 1 (마감: MM/DD)
  • [ ] 할 일 2
  • [ ] 일정: HH:MM 일정명

🚧 블로커
  • 없음 / [블로커 설명]
```

간결하게 정리하되, 중요한 것은 빠뜨리지 말 것.
