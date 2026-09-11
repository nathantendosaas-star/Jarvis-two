---
name: oops
description: "실시간 오답노트 즉시 기재 — 배치(03:15 KST)나 Stop 훅 대기 없이 지금 이 순간 실수를 4필드 규격으로 learned-mistakes.md 상단에 등재. 'oops', '오답노트에 추가', '이건 오답노트로', '실수 기록', '오답 기재' 요청 시 사용."
---

# /oops — 실시간 오답노트 즉시 기재

> 일 1회 배치(`mistake-extractor.mjs` 03:15 KST) 또는 세션 종료 훅(`stop-mistake-extract.sh`)을 기다리지 않고, **이 순간 실수를 4필드로 등재**합니다. Compound Engineering 루프의 즉시 진입점.

---

## 언제 사용합니까

- 주인님이 "이건 오답노트로", "오답노트 추가", "/oops" 라고 지시하실 때
- AI가 자기 정정("정정합니다", "오해했습니다")한 뒤 재발 방지를 남겨야 할 때
- 배치/훅이 놓쳤거나, 동일 세션 내 즉시 등재가 필요할 때

## 입력

`/oops [선택적 한 줄 요약]`

- **인자 없음**: 현재 대화 맥락에서 4필드 초안 자동 구성
- **인자 있음**: 그 한 줄을 제목 힌트로 4필드 확장

## 실행 단계

### 1. 4필드 초안 구성 (창작 금지)

대화 맥락 + 실제 파일/커밋/로그 근거만 사용. 추측·보강·창작 금지.

- **패턴**: "~하는 경향" (한 문장, 재발 가능한 행동)
- **실제**: 구체적으로 무슨 일이 있었는가 (사실 나열)
- **증거**: 주인님 원문 지적, 커밋 해시, 파일 경로, 로그 라인 (검증 가능한 것만)
- **대응**: 재발 방지 **구조** — 훅·스크립트·체크리스트·탐색 경로 고정 등. "조심하겠습니다" 같은 의지 표명은 **대응 아님**

### 2. 기존 중복 체크

`~/jarvis/runtime/wiki/meta/learned-mistakes.md`의 기존 `- **패턴**:` 라인 전체를 읽어, 65% 이상 유사한 항목이 있으면 주인님께 여쭙는다.

> "주인님, 기존 [YYYY-MM-DD 제목] 항목과 패턴이 유사합니다. (1) 새 항목으로 별도 등재 / (2) 기존 항목에 오늘자 케이스 추가, 어느 쪽이 좋으시겠습니까?"

### 3. 미리보기 + 주인님 결재 (Iron Law 3 감사 트레일)

4필드 초안을 주인님께 보여드리고 **"등재할까요?"** 확인. 승인 전 파일 변경 금지.

**승인 플래그 규칙**:
- 주인님이 미리보기 후 명시 승인 (`네`, `등재해`, `진행해`) → `approved: true`로 ledger 기록
- 주인님이 "미리보기 없이 바로" 지시한 경우에만 미리보기 생략 가능 → `approved: "preview-skipped"`로 ledger 기록 (경고 플래그)
- 어떤 경우에도 **승인 없이 임의 삽입 금지** — 위반 시 그 자체가 Iron Law 3 위반 오답 사례

### 4. 삽입

**위치**: `~/jarvis/runtime/wiki/meta/learned-mistakes.md` 최상단 (frontmatter + `# Jarvis 오답노트` + 안내 블록 다음, 첫 기존 `## YYYY-MM-DD` 항목 바로 **위**)

**포맷** (mistake-extractor.mjs가 생성하는 스키마와 100% 동일):

```markdown
## YYYY-MM-DD — <한 줄 제목>

- **패턴**: ...
- **실제**: ...
- **증거**: ...
- **대응**: ...

---
```

날짜는 KST 기준 `YYYY-MM-DD`. frontmatter의 `last_updated` 필드도 현재 KST ISO(`2026-04-21T13:45:00.000+09:00` 형식)로 갱신.

### 5. Ledger 원장 append (감사 트레일)

`~/jarvis/runtime/state/mistake-ledger.jsonl`에 한 줄 append (배치/Stop훅과 공용 SSoT):

```bash
jq -cn \
  --arg ts "$(TZ=Asia/Seoul date '+%Y-%m-%dT%H:%M:%S%z' | sed 's/\(..\)$/:\1/')" \
  --arg source "manual-oops" \
  --arg title "<제목>" \
  --arg approved "true" \
  '{ts:$ts, source:$source, count:1, titles:[$title], session_file:null, duration_s:0, approved:$approved}' \
  >> ~/jarvis/runtime/state/mistake-ledger.jsonl
```

`approved: true`는 주인님이 미리보기를 승인하신 증빙 (Iron Law 3 감사 트레일).

### 6. 확인 보고

"주인님, 오답노트에 등재 완료하였습니다. (wiki 파일: `learned-mistakes.md` 상단, RAG 인덱싱 대상, ledger 기록)"

---

## 원칙 (Iron Laws)

- **창작 금지**: 대화에 없는 실수를 만들지 않는다
- **미검증 추측 금지**: 증거 필드는 실제 파일·커밋·로그에 앵커링
- **단순 "조심"은 대응이 아니다**: 구조적 가드 필수
- **주인님 결재 우선**: 미리보기 승인 후 삽입 (Iron Law 3 준수)
- **SSoT 단일**: 기존 배치/훅과 같은 파일을 공유. 별도 저장소 만들지 않는다

## 예시

**주인님**: `/oops 크론마스터를 원장으로 오해`

**/oops 응답**:
```
주인님, 4필드 초안입니다.

## 2026-04-21 — 파일명만 보고 서브시스템 본질을 추측

- **패턴**: 산출물 파일(jsonl/state)만 발견하고 본체 에이전트 존재 미확인
- **실제**: cron-master-*.jsonl 원장 파일을 "크론마스터 자체"로 해석, 실제 셸 스크립트 본체 (~/jarvis/infra/bin/cron-master.sh, 583줄) 미탐색
- **증거**: 주인님 지적 "크론마스터 에이전트가 따로 있는거 아니었어?"
- **대응**: `*-ledger.jsonl`/`*-state.json` 발견 시 `grep -r "<파일명>" ~/jarvis/infra/{bin,scripts,agents}/` 로 생성자 스크립트 역추적 선행

등재할까요?
```

---

## 연관 시스템

| 경로 | 역할 |
|---|---|
| `~/jarvis/runtime/wiki/meta/learned-mistakes.md` | SSoT 저장소 |
| `~/jarvis/infra/scripts/mistake-extractor.mjs` | 일 1회 배치 추출 (03:15 KST) |
| `~/.claude/hooks/stop-mistake-extract.sh` | 세션 종료 직후 자동 추출 훅 |
| `/oops` (이 스킬) | 실시간 수동 진입점 |

세 경로 모두 동일 파일에 4필드 스키마로 append. 감지·트리거·진입만 다를 뿐 저장소는 하나.
