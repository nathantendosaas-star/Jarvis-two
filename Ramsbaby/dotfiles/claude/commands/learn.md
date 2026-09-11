---
description: "학습 기록 자동화 — 세션마다 발견한 패턴·실수·인사이트를 JSONL로 축적해 Compound Engineering 루프를 자동화. 'learn', '학습 기록', 'JSONL', '인사이트 축적' 요청 시 사용."
---

# /learn — 학습 기록 자동화 (JSONL + Compound Loop)

## 존재 이유

주인님, 이 스킬은 한 세션에서 얻은 깨달음이 **다음 세션에서 다시 기억나지 않는 구조적 낭비**를 막기 위해 존재합니다. Jarvis 생태계의 ETHOS는 "오답노트 → Eureka → 회고" 세 기록을 **반드시 체인으로 연결**할 때만 복리(compound)로 누적된다고 규정합니다. `/learn`은 그 체인의 **실시간 입력구(input port)** 입니다.

말로 풀자면 — 작업 도중 "어? 이거 어디서 봤는데"라는 감각이 들 때, 그 순간을 JSONL 한 줄로 강제 저장해 **다음 주, 다음 달의 저를 돕는 장치**입니다.

---

## 기존 스킬과의 경계

| 스킬 | 목적 | 호출 시점 | 산출물 |
|------|------|-----------|--------|
| `/retro` | 세션 **완료 후** 회고 + 오답노트 등록 | 세션 종료 직전 | `learned-mistakes.md` + 회고 리포트 |
| `/context-save` | 현재 세션 **스냅샷** (todo, 파일, 결정사항) | 컴팩션 직전·세션 전환 시 | `~/jarvis/runtime/context/*.md` |
| **`/learn`** | **실시간 세션 중 재사용 가능한 패턴/인사이트** 즉시 기록 | 깨달음 발생 **순간** (세션 진행 중) | `eureka.jsonl` 한 줄 append |

**한 줄 판단 기준**: "이 배움이 **다른 세션·다른 도메인에서도 재사용될 것인가**"가 Yes이면 `/learn`, "이번 세션 내부 상태"면 `/context-save`, "세션이 끝났고 돌아보는 시간"이면 `/retro`입니다.

### 기존 Eureka 시스템과의 관계

`~/jarvis/runtime/wiki/meta/eureka.jsonl`은 **이번 gstack 이식(2026-04-21 KST)과 함께 초기화된 빈 파일**입니다. 스키마는 아래 "JSONL 스키마" 절의 정의를 SSoT로 삼으며, `/learn`은 이 파일에 **append-only**로 누적합니다. 즉 본 스킬의 첫 호출부터 축적이 시작되며, 기존 레코드 호환 이슈는 없습니다.

---

## JSONL 스키마 (엄격 정의)

모든 신규 레코드는 아래 스키마를 따릅니다. 기존 필드 삭제·이름 변경 금지, **새 필드 추가만 허용**합니다.

```json
{
  "id": "eureka-YYYYMMDD-NNN",
  "date": "YYYY-MM-DD HH:MM KST",
  "type": "pattern|insight|correction|anti-pattern",
  "domain": "backend|frontend|devops|cron|db|rag|discord|apple|google|...",
  "title": "한 줄 요약 (40자 이내 권장)",
  "context": "언제·어디서 발견하였는지 (1-2문장)",
  "pattern": "무엇이 재사용 가능한 구조인지 (핵심 원리)",
  "evidence": ["증거 파일 경로", "로그 스니펫", "재현 명령"],
  "reusable_in": ["유사 상황 1", "유사 상황 2"],
  "gain": "정량 효과(예: 15분 단축) 또는 정성 효과(예: 재발 방지)",
  "source_session": "세션 ID 또는 Claude Code 대화 링크"
}
```

### 필드별 규칙

| 필드 | 필수 | 비고 |
|------|:----:|------|
| `id` | O | `eureka-` 접두 + 날짜 + 3자리 순번. 중복 금지 |
| `date` | O | **KST 필수** (UTC 금지), `date '+%Y-%m-%d %H:%M KST'` |
| `type` | O | 4종 enum 외 값 금지 |
| `domain` | O | 도메인 미상이면 `general` |
| `title` | O | 한국어, 40자 이내 권장 |
| `context` | O | "언제 발견했는가" — 트리거 맥락 |
| `pattern` | O | "무엇이 재사용 가능한가" — **이 필드가 없으면 Phase 3에서 reject** |
| `evidence` | O | 최소 1개. 빈 배열 금지 |
| `reusable_in` | O | 최소 1개. 재사용처 없으면 `/learn`이 아니라 `/retro` 대상 |
| `gain` | O | 정량/정성 중 하나 |
| `source_session` | O | 추적 불가능하면 `unknown` |

---

## Phase 0 — 트리거 감지

다음 세 가지 "감각 신호" 중 하나라도 발생하면 `/learn` 후보입니다.

1. **"어? 이거 어디서 본..."** → 기시감 (déjà vu). 이미 비슷한 문제를 풀었을 가능성 ↑
2. **"이거 다른 데서도 쓸 수 있는데"** → 재사용 가능성 포착
3. **"아 이게 원인이었구나"** → 근본 원인 최초 확정 (correction 후보)

신호 감지 시 즉시 작업을 멈추지는 않고, **현재 블록이 끝나는 지점**에서 `/learn`을 호출합니다. 작업 흐름을 끊지 않는 것이 원칙입니다.

---

## Phase 1 — 분류

`type` 4종 중 하나로 분류합니다.

| type | 정의 | 예시 |
|------|------|------|
| `pattern` | 반복 재사용 가능한 **성공 구조** | "LaunchAgent plist는 `ai.jarvis.[서비스명]` 패턴" |
| `insight` | 관점 전환형 깨달음 (구조는 없지만 시각이 바뀜) | "RAG 리콜 저하는 쿼리가 아닌 청크 크기 문제였음" |
| `correction` | 과거 판단/문서/기록의 **오류 정정** | "plist 경로는 `~/Library`가 아니라 `/Library/LaunchAgents`였음" |
| `anti-pattern` | 반복적으로 실패하는 **반면교사 구조** | "try/except로 예외 삼키기 → Iron Law 1 위반" |

판단 기준 한 줄: 성공 재현 → `pattern` / 시각 전환 → `insight` / 과거 오류 정정 → `correction` / 재현 실패 → `anti-pattern`.

---

## Phase 2 — JSONL 레코드 작성

스키마 준수 필수. 예시는 다음과 같습니다.

```json
{"id":"eureka-20260421-001","date":"2026-04-21 14:32 KST","type":"pattern","domain":"cron","title":"LaunchAgent 재시작은 unload→load 2단계 필수","context":"ai.jarvis.discord-bot plist 변경 후 재시작이 반영되지 않음","pattern":"launchctl bootout + bootstrap 2단계. 단일 kickstart로는 plist 재로드 안 됨","evidence":["~/jarvis/infra/scripts/discord-bot-restart.sh:42","man launchctl"],"reusable_in":["모든 LaunchAgent 재시작","watchdog 재배포"],"gain":"재시작 실패 재현율 0%","source_session":"claude-session-20260421-a"}
```

**주의**: 한 줄(single-line) JSON이어야 합니다. 줄바꿈이 들어가면 JSONL 파서가 깨집니다.

---

## Phase 3 — 중복 체크

기존 `eureka.jsonl`에 유사 항목이 있으면 **신규 append 대신 병합 제안**합니다.

```bash
jq -c "select(.title | contains(\"$NEW_TITLE_KEYWORD\"))" \
  ~/jarvis/runtime/wiki/meta/eureka.jsonl

jq -c "select(.domain==\"$NEW_DOMAIN\") | {id,title,pattern}" \
  ~/jarvis/runtime/wiki/meta/eureka.jsonl
```

후보가 나오면 주인님께 세 옵션으로 여쭙습니다.

- A) **신규 append** — 별개 케이스로 판단
- B) **기존 레코드 업데이트** — 기존 id 유지, 새 `evidence`/`reusable_in`를 병합 (append-only 정책상, 새 id로 쓰되 `supersedes` 필드로 연결)
- C) **기각** — 중복이라 기록 불필요

판단 근거도 함께 제시합니다 (유사도, 도메인 일치 여부, pattern 핵심 단어).

---

## Phase 4 — 파일 append

**JSON 문법 검증이 반드시 선행**됩니다. 깨진 JSON을 append하면 전체 파일이 손상될 수 있습니다.

```bash
NEW='{"id":"eureka-20260421-001","date":"2026-04-21 14:32 KST", ...}'

# 1) JSON 문법 선검증 (깨진 JSON 차단)
echo "$NEW" | jq -e . > /dev/null || { echo "JSON 문법 오류 — append 차단"; exit 1; }

# 2) flock 배타 락으로 동시 append 경합 제거 (JSONL race condition 방지)
EUREKA=~/jarvis/runtime/wiki/meta/eureka.jsonl
LOCK="${EUREKA}.lock"
(
  flock -x -w 5 9 || { echo "flock 타임아웃 (5s) — append 포기"; exit 3; }
  echo "$NEW" | jq -c . >> "$EUREKA"
) 9>"$LOCK"

# 3) 파일 전체 무결성 재검증 (락 해제 후)
jq . "$EUREKA" > /dev/null \
  || { echo "파일 손상 감지 — 즉시 롤백 필요"; exit 2; }
```

> **동시성 가드 근거**: `/learn` 은 수동 호출 + 주간 집계 크론 + `/retro` 체인 호출 등 **복수 경로**에서 호출될 수 있습니다. 단순 `>>` append 는 JSONL 한 줄 중간에 다른 프로세스 쓰기가 끼어들어 파일이 손상될 수 있으므로 `flock -x` 로 배타 락을 강제합니다.

### 추가 복제 규칙

- `type`이 `correction` 또는 `anti-pattern`이면 **오답노트에도 복제**합니다.
  - 대상: `~/jarvis/runtime/wiki/meta/learned-mistakes.md`
  - 포맷: `- [YYYY-MM-DD KST] [correction] title — pattern (→ eureka id)`
- `type`이 `pattern` 또는 `insight`이면 eureka.jsonl **단독 기록**으로 충분합니다.

---

## Phase 5 — 주인님 브리핑

레코드 저장 직후, 다음 3줄 요약을 보고드립니다.

1. **저장 완료 보고**: `eureka-YYYYMMDD-NNN | type | domain | title`
2. **이번 주 누적 학습 건수**: `jq -c '.' eureka.jsonl | wc -l` 결과 중 최근 7일치
3. **연계 행동 제안**: 월요일 주간 집계 크론과 연계되어 Discord 브리핑에 자동 포함될 예정 — 확인 채널: `jarvis-system`

### 주간 집계 크론 연계 (선택)

주간 크론(`jarvis-weekly-learn-digest`, 아직 미구현일 수 있음)이 존재한다면 매주 월요일 09:00 KST에 지난 7일의 `eureka.jsonl` 엔트리를 집계해 Discord `jarvis-system` 채널로 송출합니다. 구현 상태는 `crontab -l | grep learn` 또는 LaunchAgent 목록으로 확인합니다.

---

## Jarvis 기존 자산 연계

| 자산 | 경로 | `/learn` 역할 |
|------|------|---------------|
| Eureka 로그 | `~/jarvis/runtime/wiki/meta/eureka.jsonl` | **신규 append 대상 (SSoT)** |
| 오답노트 | `~/jarvis/runtime/wiki/meta/learned-mistakes.md` | `correction`·`anti-pattern` 복제 대상 |
| 회고 리포트 | `/retro` 산출물 | 세션 종료 시 `/learn` 결과 참조·요약 |
| 주간 집계 | `jarvis-weekly-learn-digest` 크론 (계획) | Phase 5 브리핑의 정기 송출 경로 |

---

## 명령어 레퍼런스

### 새 레코드 append (검증 포함)
```bash
NEW='{"id":"eureka-20260421-001", ...}'
EUREKA=~/jarvis/runtime/wiki/meta/eureka.jsonl

echo "$NEW" | jq -e . > /dev/null || { echo "JSON 오류 — append 차단"; exit 1; }

(
  flock -x -w 5 9 || { echo "flock 타임아웃"; exit 3; }
  echo "$NEW" | jq -c . >> "$EUREKA"
) 9>"${EUREKA}.lock"
```

### 전체 파일 무결성 검증
```bash
jq . ~/jarvis/runtime/wiki/meta/eureka.jsonl > /dev/null && echo "OK" || echo "손상"
```

### 도메인별 검색
```bash
jq 'select(.domain=="backend")' ~/jarvis/runtime/wiki/meta/eureka.jsonl
```

### type별 카운트
```bash
jq -r '.type' ~/jarvis/runtime/wiki/meta/eureka.jsonl | sort | uniq -c
```

### 최근 7일치 요약
```bash
SINCE=$(date -v-7d '+%Y-%m-%d')
jq -c "select(.date >= \"$SINCE\") | {id, type, title}" \
  ~/jarvis/runtime/wiki/meta/eureka.jsonl
```

### 중복 후보 찾기
```bash
jq -c "select(.title | test(\"재시작\"))" \
  ~/jarvis/runtime/wiki/meta/eureka.jsonl
```

---

## 금지 사항

1. **기존 스키마 파괴 금지** — 필드 삭제·이름 변경 금지. 새 필드 **추가만** 허용 (backward compatible).
2. **외부 gstack bin 의존 금지** — `gstack-learnings-log`, `gstack-learnings-search` 등 호출 금지. Jarvis는 `jq` + 쉘만으로 자립해야 합니다.
3. **중복 레코드 추가 금지** — Phase 3 중복 체크 의무 수행. 병합 대신 무분별 append 금지.
4. **JSON 문법 오류 append 차단** — `jq -e .` 검증 실패 시 반드시 append 중단.
5. **UTC 시간 표기 금지** — 모든 `date` 필드는 KST (ETHOS 시간 표기 규칙).
6. **시크릿 포함 금지** — `evidence`에 토큰·API 키·비밀번호 절대 금지 (Iron Law 4).
7. **근거 없는 `pattern` 금지** — `evidence` 배열이 비어 있으면 레코드 자체를 거부합니다 (Iron Law 6: 선언 전 검증).

---

## 자기검열 체크 — append 직전 필수

1. `pattern` 필드가 "**다른 세션에서도 꺼내쓸 수 있는 구조**"인가? 단순 이번 작업 메모면 `/learn`이 아닌 `/context-save` 대상입니다.
2. `evidence`에 **시크릿·PII가 섞이지 않았는가**?
3. `type`이 `correction`·`anti-pattern`인데 **오답노트 복제를 잊지 않았는가**?
4. `date`가 **KST**인가? UTC 금지.
5. `id`가 기존 eureka.jsonl과 **중복되지 않는가**?

다섯 항목 모두 통과해야 append합니다.

---

## 호출 예시

### 예시 1 — 패턴 기록

> 주인님: "방금 Discord 봇 재시작할 때 launchctl bootout 없이 kickstart만 했더니 plist 반영이 안 됐어. 이거 기록해둬."

→ `/learn` 호출 → `type: pattern` / `domain: cron` / `title: "LaunchAgent 재시작은 bootout→bootstrap 2단계 필수"` → Phase 3 중복 체크 → 없음 확인 → Phase 4 append → Phase 5 브리핑.

### 예시 2 — 오답 정정

> 주인님: "plist 경로 내가 `~/Library`라고 알려줬던 거 틀렸어. 시스템 서비스는 `/Library/LaunchAgents`야."

→ `/learn` 호출 → `type: correction` / `domain: devops` → eureka.jsonl append + **learned-mistakes.md에도 복제** → "기존 문서 중 잘못된 경로 언급 파일 3건을 검색해 수정 대상으로 보고".

### 예시 3 — 안티패턴 발견

> 주인님: "RAG 인덱싱 실패인데 try/except로 에러 삼키고 있었더라. 이거 반면교사로 남겨."

→ `/learn` 호출 → `type: anti-pattern` / `domain: rag` → eureka.jsonl + learned-mistakes.md 양쪽 기록 → Iron Law 1 위반 사례로 교차 참조 주석 포함.

### 쉬운 말로 한 줄 요약

> `/learn`은 **"지금 이 깨달음, 나중의 내가 반드시 다시 꺼내쓰게 만드는 도구"** 입니다. 세션 도중 작은 유레카가 올 때 한 줄 JSON으로 저장해, 다음 주 월요일 Discord 브리핑과 크론 집계로 자동 복기되도록 연결합니다.

---

**참조**: `~/.claude/rules/jarvis-ethos.md` (Compound Engineering 섹션), `~/.claude/rules/jarvis-core.md` (SSoT/DRY), `~/.claude/rules/jarvis-persona.md` (보고 양식).

---

## 🗒️ CE훅 섹션 생략 사유

본 문서(`/learn` 스킬)는 **Compound Engineering 훅의 주관자** 자신이므로, 다른 6개 스킬(investigate/ship/context-save/context-restore/retro/office-hours)에 부착한 "## 📚 Compound Engineering 훅" 표준 블록은 **의도적으로 생략**합니다. `/learn`이 곧 CE훅의 실행 경로이며, 자기참조 블록은 중복 정보로 판단했습니다.

---

## 🏢 조직도·결재 연계

본 스킬은 **자비스 컴퍼니** 조직도 상 **비서실장(Sonnet)** 주관으로 실행되며, 결재 레벨은 다음과 같습니다.

- **L1 (자율실행)**: 패턴·insight 드래프트, 중복 검색 질의 수행
- **L2 (실행 후 보고)**: eureka.jsonl에 신규 레코드 append(스키마 검증 통과 시)
- **L3 (비서실장 승인)**: `type=correction|anti-pattern` 레코드의 learned-mistakes.md 복제
- **L4 (주인님 결재)**: 스키마 변경(필드 추가 외), 기존 레코드 삭제·수정
- **CEO(Opus) 에스컬레이션**: 주간 집계 크론(`jarvis-weekly-learn-digest`) 정책 변경, 장기 학습 자산의 아카이브·압축 판단
