# integrations

## 기기 환경 및 도구 선택 원칙

| 기기 | Apple Notes | Apple Reminders | Google Tasks | Google Calendar |
|------|:-----------:|:---------------:|:------------:|:---------------:|
| MacBook / Mac Mini | O | O | O | O |
| Galaxy | X | X | O | O |

**결론**: 할일/태스크는 `gog tasks` 권장 (모든 기기 동기화).

---

## Apple 연동

### memo — Apple Notes CLI v0.3.3

```bash
memo search "키워드"      # 노트 검색
memo folders              # 폴더 목록
memo list                 # 노트 목록
memo create               # 새 노트 생성
```

### remindctl — Apple Reminders CLI v0.1.1

```bash
remindctl lists           # 목록 조회
remindctl list "목록명"   # 특정 목록 항목 조회
remindctl add "항목"      # 항목 추가
remindctl complete "ID"   # 완료 처리
```

> **주의**: iCloud 동기화, Apple 전용. Galaxy 비호환.

---

## Google Workspace 연동 (gog)

### gog tasks — Google Tasks

기본 목록 ID: `MDE3MjE5NzU0MjA3NTAxOTg4ODc6MDow`

```bash
gog tasks lists                                              # 목록 조회
gog tasks list "MDE3MjE5NzU0MjA3NTAxOTg4ODc6MDow"           # 항목 조회
gog tasks add "MDE3MjE5NzU0MjA3NTAxOTg4ODc6MDow" \
  --title "할일 제목" --due "2026-04-01"                    # 항목 추가
gog tasks done "목록ID" "할일ID"                             # 완료 처리
```

### gog cal — Google Calendar

```bash
gog calendar list \
  --from today --to today \
  --account ${GOOGLE_ACCOUNT}    # 오늘 일정 조회

gog cal add \
  --title "회의" \
  --start "2026-02-05 14:00" \
  --end "2026-02-05 15:00"           # 일정 추가
```
