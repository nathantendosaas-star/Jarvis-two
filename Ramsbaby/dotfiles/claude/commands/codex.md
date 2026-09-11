---
description: "코드 작업 표준 프로토콜 — 기능 추가·리팩터·버그 수정 시 일관된 탐색/수정/검증 체크리스트. 'codex', '코드 작업', '표준 프로토콜', '코딩 표준' 요청 시 사용."
---

# /codex — 코드 작업 표준 프로토콜

## 정체성과 목적

주인님께서 코드 작업(기능 추가, 리팩터링, 버그 수정)을 요청하셨을 때, 즉흥적으로 파일을 고치지 않고 **탐색 → 계획 → 수정 → 검증 → 보고**의 일관된 6단계 프로토콜을 따르는 스킬입니다.

`/codex`는 "어떻게 작업하느냐"의 규율을 담보합니다. 산출물은 변경된 코드와 검증 증거, 그리고 학습 기록입니다.

---

## 기존 스킬과의 경계 (중요)

혼동을 막기 위해 명시합니다.

| 스킬 | 역할 | /codex와의 차이 |
|------|------|------------------|
| `/review` | 이미 완료된 코드를 Dev+Reviewer 에이전트로 리뷰 | /codex는 **진행 중** 작업의 표준 절차 |
| `/sdd` | Task→Dev→Feature→인수테스트의 스펙부터 시작하는 프로세스 | /codex는 **스펙이 이미 확정된** 코드 작업의 절차 |
| `/investigate` | 5 Why로 **근본 원인**을 파고드는 디버깅 | /codex는 원인이 파악된 뒤 **수정 실행** 절차 |
| `/simplify` | 이미 작성된 코드의 단순화·재사용성 점검 | /codex는 **신규·수정 작업** 전체 사이클 |

**판단 기준**:
- 완성된 PR을 리뷰하고 싶다 → `/review`
- 새 기능을 스펙부터 만든다 → `/sdd`
- 원인을 모르는 장애를 추적한다 → `/investigate`
- 기능 추가·리팩터·버그 수정 코드 작업을 한다 → **`/codex`**

---

## Phase 0 — 사전 점검 (Jarvis 특화 3종 통합)

작업 시작 전 반드시 다음 3가지를 조회합니다.

### 0-1. 오답노트 스캔

```bash
LEARNED=$HOME/jarvis/runtime/wiki/meta/learned-mistakes.md
if [ -f "$LEARNED" ]; then
  grep -i -E "<작업 도메인 키워드>" "$LEARNED" | head -10
fi
```

- 유사 실수 패턴이 있으면 **Phase 3 수정 단계에 가드 체크리스트로 삽입**
- 대표적 패턴 예: "3단계 파이프라인 부분 실행", "Virtual Thread + HikariCP 고갈", "좀비 캐시"

### 0-2. Eureka 재사용 패턴 검색

```bash
EUREKA=$HOME/jarvis/runtime/wiki/meta/eureka.jsonl
if [ -f "$EUREKA" ]; then
  grep -i -E "<도메인 키워드>" "$EUREKA" | tail -5
fi
```

- 과거에 성공한 접근법이 있으면 우선 재사용 후보
- 없으면 신규 학습 수확 대상으로 표시

### 0-3. 조직도 포지셔닝

- 단순 국소 수정(파일 1~2개): 비서실장(Sonnet) 자율 진행 → **L1 또는 L2**
- 파이프라인·스키마·보안 영향: 비서실장 승인 필요 → **L3**
- 프로덕션 배포·데이터 삭제·결제 로직: 주인님 결재 필요 → **L4**

작업 범위가 L3~L4에 해당하면 Phase 2 계획 단계에서 승인 경로를 명시합니다.

---

## Phase 1 — 탐색 (Glob → Grep → Read, 효율 우선)

### 원칙

1. **전체 파일 Read 금지**(최후 수단). 심볼 단위로 접근합니다.
2. **Serena 우선**: `get_symbols_overview → find_symbol(include_body=true) → find_referencing_symbols` 순서.
3. Serena가 부적절한 파일 유형(MD, JSON, shell)이면 **Glob → Grep**으로 좁힌 뒤 필요한 부분만 Read.

### 기본 순서

```
1. Glob으로 대상 파일/디렉토리 후보 좁히기
   예: Glob("src/**/*.service.ts")

2. Grep으로 키워드·심볼 위치 특정
   예: Grep("deductBalance", type="ts", output_mode="content", -n=true)

3. Serena find_symbol로 의미 단위 조회
   예: find_symbol("PaymentService/deductBalance", include_body=true)

4. 참조 관계 확인
   예: find_referencing_symbols("PaymentService/deductBalance")

5. 필요한 부분만 Read (offset/limit 활용)
```

### 탐색 산출물

Phase 2에서 참조할 "영향 범위 맵"을 메모장에 기록합니다.

- 직접 수정 대상 파일
- 간접 영향 파일(참조·테스트·마이그레이션)
- 위험 신호(트랜잭션 경계, 동시성, 외부 호출)

---

## Phase 2 — 계획 (수정 전 반드시 명시)

Phase 1 결과를 바탕으로 다음을 작성합니다.

### 계획서 필수 필드

```markdown
### 목적
<한 줄: 왜 이 변경이 필요한가>

### 영향 범위
- 직접 수정: path/to/file1.ts, path/to/file2.ts
- 간접 영향: path/to/test1.spec.ts, path/to/migration.sql
- 재사용할 Eureka 패턴: <있으면 명시>

### 변경 방식
- 기능 추가 / 리팩터 / 버그 수정 중 하나
- Breaking change 여부 (있다면 호환성 대비책)

### 오답노트 가드
- 관련 실수 패턴: <Phase 0-1 결과>
- 적용할 가드: <테스트 보강 · 트랜잭션 경계 검증 · 롤백 절차>

### 검증 계획
- 단위 테스트: <어떤 케이스>
- 통합 테스트: <어떤 경로>
- 수동 확인: <필요하면>

### 결재 레벨
- L1 / L2 / L3 / L4 중 하나 + 근거
```

### 원칙

- **수정 범위가 커지면 쪼개기**: 계획이 3단계 이상이면 커밋도 3번 이상 예정.
- **Breaking change는 호환성 섹션 필수**: 구버전 호출자 처리, 마이그레이션 순서.
- **L3 이상이면 계획 확정 전 주인님께 미리보기**.

---

## Phase 3 — 수정 (Edit 우선, Write는 전면 재작성만)

### 도구 선택 규칙

| 상황 | 도구 |
|------|------|
| 기존 심볼 바디 교체 | Serena `replace_symbol_body` |
| 심볼 삽입 | Serena `insert_after_symbol` / `insert_before_symbol` |
| 부분 문자열 치환 | `Edit` (old_string / new_string) |
| 파일 전체 재작성 | `Write` (최후 수단, 신규 파일 생성 시) |

### 안전 원칙

1. **Edit 한 번에 한 관심사만**. 여러 변경을 한 Edit에 섞지 않음.
2. **Write는 기존 파일 대체 시 반드시 사전 Read**(도구 제약 + 의도적 복구).
3. **집단 rename은 `replace_all=true`** 사용. Edit 반복 금지.
4. **커밋 경계 유지**: Phase 2에서 예정한 커밋 단위로 수정을 묶습니다.

### 오답노트 기반 가드 재확인

수정 완료 직전, Phase 0-1에서 발견된 실수 패턴을 다시 한 번 체크리스트로 점검합니다.

예시 체크리스트:
- [ ] 3단계 파이프라인(`tasks.json` → `plugin-loader` → `cron-sync`) 누락 없음
- [ ] 트랜잭션 경계에 `REQUIRES_NEW` 필요 여부 재검토
- [ ] 동시성 변경 시 `SADD/SREM` 계열 원자 연산 확인
- [ ] 캐시 TTL 관련 변경 시 좀비 캐시 회귀 테스트

### 🚨 파라미터·설정 복사 시 용도 검증 (2026-04-24 재발 방지 룰)

기존 함수/SDK 예제에서 **파라미터(maxTurns, allowedTools, timeout 등)를 복사할 때**, 원 함수의 용도와 내 용도가 다를 수 있습니다. 2026-04-24 `claude-runner.js:534 autoExtractMemory(maxTurns:1)` 을 Discord 스킬 runner로 복사하여 `/doctor`·`/deploy` 실 호출 exception 발생 사고.

**복사 전 3단계 자문**:
1. **원 함수의 용도는?** (예: "autoExtractMemory = JSON 추출 1턴용 경량 호출")
2. **내 용도는?** (예: "스킬 runner = 대화형 여러 턴 필요")
3. **파라미터 의미가 두 용도에서 동일한가?** 다르면 내 용도 기준 **역으로 도출**.

**강제 주석**: 특이 파라미터는 주석에 "왜 이 값인가?" 근거 기재.
```js
// maxTurns: 10 — 스킬은 대화형 여러 턴 필요. autoExtractMemory의 1턴 스펙과 다름.
maxTurns: options.maxTurns || 10,
```

**체크 타이밍**: Phase 3 수정 중 새 SDK·외부 라이브러리 설정 추가 시 본 가드 **건너뛰기 금지**.

---

## Phase 4 — 검증 (변경 후 반드시 증거 수집)

### 검증 3층

1. **정적**: 컴파일/린트/타입 체크(`tsc --noEmit`, `eslint`, `mypy` 등).
2. **동적**: 관련 단위·통합 테스트.
3. **실사용**: 로컬 실행·smoke test·로그 확인.

### 산출물

```markdown
### 검증 결과
- tsc: PASS (0 errors)
- eslint: PASS (0 warnings)
- unit tests: 42/42 PASS
- integration: 8/8 PASS
- smoke: <명령어 + 결과 요약>
```

### 실패 처리

- **하나라도 실패하면 Phase 3로 돌아감**. 커밋 금지.
- 실패가 기존 버그(내 변경과 무관)로 판명되면 별도 티켓 생성 후 진행.
- 실패 원인을 파악하지 못한 채 무시하고 진행하는 것은 **Iron Law 위반**.

---

## Phase 5 — 보고·학습

### 5-1. 주인님 보고 포맷

```markdown
## 작업 완료 보고

### 변경 요약
- <파일 N개, +X/-Y 라인>
- 핵심 변경: <한 문장>

### 검증 증거
- <tsc/lint/test 결과 링크>

### 커밋 분리
- commit 1: <요약>
- commit 2: <요약>

### 후속 조치
- 필요하면 `/ship`으로 릴리즈
- 문제 발견되면 `/retro`로 오답노트 등록
```

### 5-2. 학습 수확(Compound Engineering)

재사용 가치가 있는 패턴을 발견하면 **Eureka 후보로 기록**합니다.

```bash
# 패턴 요약을 eureka.jsonl 후보로 메모
EUREKA=$HOME/jarvis/runtime/wiki/meta/eureka.jsonl
echo '{"date":"YYYY-MM-DD","pattern":"<패턴 요약>","context":"<적용 맥락>","gain":"<정량 효과>"}' >> "$EUREKA.candidate"
```

- 최종 등록은 `/retro`에서 주인님 승인 후 반영.

### 5-3. 오답노트 등록(실수가 있었던 경우)

작업 중 삽질이 있었다면 **반드시 오답노트 등록 후보**로 올립니다.

```markdown
## YYYY-MM-DD — <한 줄 제목>

- **패턴**: <어떤 가정이 틀렸는가>
- **실제**: <실제로 무엇이 필요했는가>
- **증거**: <로그·커밋·재현 절차>
- **대응**: <앞으로 무엇을 체크할 것인가>
```

- 최종 등록은 `/retro`에서 진행.

---

## Phase 6 — 결재 및 마무리

작업 완료 후 결재 레벨에 따라:

- **L1 (자율)**: 보고만 하고 종료.
- **L2 (실행 후 보고)**: 실행 결과 요약 + 롤백 절차 명시.
- **L3 (비서실장 승인)**: 커밋 전에 승인 대기 표시 후 주인님 승인 요청.
- **L4 (주인님 결재)**: 주인님께서 직접 `git push` 또는 배포 승인하실 수 있도록 대기.

---

## 중단 및 롤백 기준

다음 상황에서는 즉시 중단하고 주인님께 보고합니다.

1. Phase 1 탐색 결과 **영향 범위가 Phase 0 추정의 3배 이상**인 경우.
2. Phase 4 검증이 **기존 테스트 회귀**를 유발한 경우.
3. 수정 중 **비밀키·크리덴셜**을 발견한 경우 (즉시 `/cso`로 이관).
4. Phase 2 계획 단계에서 **오답노트의 강력한 경고**가 발견된 경우 (예: "3단계 파이프라인 부분 실행").

롤백 절차:
```bash
git restore <파일>     # 미커밋 변경 되돌리기
git reset HEAD~1       # 커밋만 취소(변경은 보존)
git reset --hard HEAD~1  # 커밋과 변경 모두 폐기 (사전 승인 필수)
```

---

## Iron Law 준수

- **NO FIXES WITHOUT ROOT CAUSE**: 원인이 불명확한 수정은 하지 않음. 필요하면 `/investigate` 선행.
- **VERIFY BEFORE DECLARE**: 검증 없이 "완료" 선언 금지.
- **NEVER LIE ABOUT STATUS**: 부분 성공은 "부분 성공"으로 보고.

---

## 호출 예시

- "이 함수 리팩터해줘" → `/codex` 로 Phase 1 탐색부터 시작.
- "결제 배치에 SQS 재시도 추가" → `/codex` + 결재 L3 판정.
- "주석만 고쳐줘" → `/codex` 생략 가능(1~2줄 trivial 수정).

**쉬운 말로**: 코드 작업할 때 무턱대고 고치지 말고, 먼저 훑고(Phase 1) → 계획 세우고(Phase 2) → 고치고(Phase 3) → 돌려보고(Phase 4) → 보고하기(Phase 5~6). 주인님 일관성 방어선입니다.
