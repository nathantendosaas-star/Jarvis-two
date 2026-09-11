---
description: "설계·기획서 엄격 리뷰. 11섹션 체크리스트로 아키텍처·보안·배포까지 빠짐없이 검증. '설계 리뷰', '기획 검토', 'plan review', '제대로 봐줘', '이 기획 괜찮아?' 요청 시 사용. (gstack plan-ceo-review 한국어 이식)"
---

# Plan Review — 11섹션 엄격 설계 검토

이 커맨드는 gstack의 `/plan-ceo-review`를 Jarvis 페르소나·한국어 환경에 맞춰 이식한 것입니다.
**목적은 도장 찍기가 아니라 설계를 "이 바닥 최고 수준"으로 끌어올리는 것**입니다.

---

## 🎯 발동 조건

- 기능 설계서·기획서·아키텍처 RFC 작성 후 검토 요청
- "이 접근 괜찮아?" / "놓친 거 없어?" / "더 나은 방법?" 질문
- 구현 착수 직전 (코드 쓰기 전 마지막 관문)

**착수 직전 호출 권장** — 구현 시작 후 되돌리기 비용이 기하급수적으로 증가합니다.

---

## 🧭 Phase 0 — Scope 모드 선택 (필수)

사용자에게 반드시 AskUserQuestion으로 다음 4가지 중 하나를 선택받으십시오.
모드 선택 후에는 **중간에 표류 금지** — 섹션 리뷰가 끝날 때까지 해당 포지션 유지.

### 🚀 확장 모드 (SCOPE EXPANSION)
- **입장**: "성당을 짓습니다. 이상적 버전은 무엇인가?"
- **질문 형식**: "2배 노력으로 10배 효과를 내려면 무엇을 추가해야 합니까?"
- **출력**: 각 확장 아이디어를 개별 opt-in 질문으로 제시
- **적합**: 신규 제품, 장기 베팅, 주인님이 "더 크게 생각해보고 싶다" 할 때

### 🎯 선택적 확장 모드 (SELECTIVE EXPANSION)
- **입장**: "기본선은 철벽 방어. 부가 기회는 체리픽."
- **질문 형식**: "기본 범위를 유지하되, 눈에 띄는 기회마다 개별 질문으로 수락/거절"
- **출력**: 기본 리뷰 + 확장 기회 리스트 (각각 노력/리스크 명시)
- **적합**: 출시 임박, 범위는 대체로 정해졌으나 추가 여지 탐색 원할 때

### 🔒 고정 모드 (HOLD SCOPE)
- **입장**: "범위는 확정. 실패 모드 전부 박멸."
- **질문 형식**: 범위 확장·축소 제안 금지. 순수 엄격 검증만.
- **출력**: 11섹션 전수 조사, 발견 이슈만 나열
- **적합**: 마감 임박, 일정 변경 불가, 기능은 고정

### ✂️ 축소 모드 (SCOPE REDUCTION)
- **입장**: "외과의. 핵심 외 전부 절단."
- **질문 형식**: "이 기능 빼도 핵심 결과 달성되는가?"
- **출력**: 현재 범위의 70%를 잘라낸 MVP 제안
- **적합**: 리소스 부족, 일정 압박, "일단 최소만 출시"

### ⚠️ 모드 선택 없이 진행 금지

Scope 모드가 정해지지 않으면 리뷰 관점이 흔들립니다. **반드시 먼저 선택받으십시오.**

---

## 🏛️ Prime Directives (리뷰 전체에 적용)

1. **Zero silent failures** — 모든 실패 모드가 가시적이어야. 조용히 실패할 수 있으면 치명적 결함.
2. **Every error has a name** — "에러 처리" 금지. 구체적 예외 클래스·트리거·캐치·사용자 노출·테스트 여부 명시.
3. **Data flows have shadow paths** — 모든 데이터 흐름엔 happy + nil + empty + upstream error 4경로. 전부 추적.
4. **Interactions have edge cases** — 더블클릭, 중간 이탈, 느린 연결, stale state, 뒤로가기 매핑 필수.
5. **Observability is scope** — 로그·메트릭·알림·런북은 출시 후 정리가 아닌 **1등 인도물**.
6. **Diagrams are mandatory** — ASCII 다이어그램 필수: 데이터 흐름, 상태 머신, 처리 파이프라인, 의존 그래프.
7. **TODOS.md or it doesn't exist** — 보류한 것은 전부 기록. 막연한 의도는 거짓말.
8. **Optimize for 6-month future** — 오늘 해결하고 다음 분기 악몽 만들면 명시.
9. **"Scrap it and do this instead" 권한** — 근본적으로 더 나은 접근이 있으면 즉시 제안.

---

## 📋 Phase 1 — 11섹션 체크리스트

각 섹션마다 다음 순서:
1. **질문 던지기** (해당 항목 커버되었는지)
2. **누락·결함 발견 시** AskUserQuestion으로 개별 opt-in 수락 받기
3. **배칭·스킵 금지** — 한 섹션의 이슈는 그 자리에서 해결

### ① 아키텍처 (Architecture)

- 의존 그래프: 순환 의존성 없는가?
- 데이터 흐름 ASCII: 입력 → 처리 → 출력 전부 그렸는가?
- 상태 머신: 상태 전이 모든 조합 매핑했는가?
- 실패 시나리오: 각 컴포넌트 장애 시 전파 경로 추적했는가?
- 롤백 자세: 이 설계를 취소하려면 어떻게 되는가? (reversibility)

### ② 에러 & 복구 맵 (Error & Rescue Map)

- 발생 가능한 예외 전수 나열 (구체 클래스명)
- 각 예외의 캐치 위치 / 사용자 노출 메시지 / 재시도 로직
- **Catch-all 금지**: `catch Exception` / `except:` / `catch (error)` 단독 사용 → 코드 스멜
- 타임아웃 값이 명시되어 있는가? (HTTP / DB / 외부 API / 내부 큐)
- 부분 실패 처리: 3개 작업 중 2개만 성공 시 어떻게?

### ③ 보안 & 위협 모델 (Security & Threat Model)

- 공격 표면 (attack surface): 신뢰 경계 어디인가?
- 입력 검증: 모든 외부 입력 sanitize 되는가?
- 인증·인가: 누가 무엇을 할 수 있는가? RBAC/ABAC 명시.
- 비밀 관리: API 키·토큰 하드코딩 없는가? 환경변수/시크릿 매니저 사용?
- 인젝션 벡터: SQL / NoSQL / Command / XSS / SSRF / Path Traversal
- OWASP Top 10 체크 (해당 항목만 선택)

### ④ 데이터 흐름 엣지케이스 (Data Flow Edge Cases)

- 더블 클릭 / 중복 요청 멱등성 보장?
- 네비게이트-어웨이 중간 이탈 시 데이터 일관성?
- Stale state: 탭 여러 개, 오래된 상태로 작업 시?
- Zero/empty 결과: 빈 배열, null, 0건 응답 시 UX?
- 동시성: 같은 리소스 동시 수정 시 Race Condition?

### ⑤ 코드 품질 (Code Quality)

- SSoT(Single Source of Truth): 중복 정의 없는가?
- DRY: 3회 이상 반복 로직 함수 추출했는가?
- 명명: 변수·함수·클래스 명 일관성
- 복잡도: cyclomatic complexity 과하지 않은가? (함수당 10 초과 경고)
- 프래질리티 체크: 작은 변경에 전체 깨지는 구조 아닌가?

### ⑥ 테스트 (Test Review)

- 새로 추가되는 것 전부 다이어그램으로 정리
- 각 항목의 테스트 커버리지 명시 (유닛/통합/E2E)
- 누락된 테스트: "작성 예정"이 아닌 구체적 파일명
- 엣지케이스 테스트: happy path 외 3개 shadow path 테스트 있는가?
- 성능 회귀 테스트 필요한 부분 명시

### ⑦ 성능 (Performance)

- N+1 쿼리 가능성? → 배치/JOIN으로 변경
- 인덱싱: 새 쿼리의 EXPLAIN 계획 확인했는가?
- 캐싱 전략: Redis/CDN 사용 시 TTL·Invalidation 명시
- 커넥션 풀: DB / HTTP 클라이언트 풀 사이즈 적정?
- p50/p95/p99 목표 지연시간 명시

### ⑧ 관측성 (Observability)

- 로그: 어떤 이벤트를 어느 레벨로? (INFO/WARN/ERROR)
- 메트릭: 핵심 지표 (에러율, 처리량, 지연시간) 노출?
- 트레이싱: 분산 추적 ID 전파?
- 알림: 어느 임계값에서 PagerDuty/Slack?
- 대시보드: 누가 무엇을 볼 수 있는가?
- 런북: 장애 시 대응 절차 문서?

### ⑨ 배포·롤백 (Deployment & Rollout)

- 마이그레이션: DB 스키마 변경 시 순서 (add column → backfill → code → drop)
- 피처 플래그: 배포 ≠ 릴리즈. 점진 롤아웃 가능?
- 제로 다운타임: ALB draining / blue-green / canary 중 선택?
- 롤백 계획: 10분 내 이전 버전 복귀 가능?
- 스모크 테스트: 배포 후 즉시 검증 스크립트?

### ⑩ 장기 궤적 (Long-Term Trajectory)

- 기술 부채: 이 설계가 6개월 뒤 어떤 부채를 만드는가?
- 역전 가능성: 이 선택을 나중에 되돌리는 비용?
- 생태계 적합: 팀의 기존 기술 스택·패턴과 일치?
- Phase 2 사고: 이 기능의 다음 단계는 무엇? 미리 설계 고려?

### ⑪ 디자인 & UX (Design & UX) — UI 관련 시만

- 정보 계층: 사용자가 가장 중요한 것을 먼저 보는가?
- 상태 커버리지: loading / empty / error / success 전부 디자인?
- 사용자 여정: 첫 진입 → 완료까지 클릭 수 최소화?
- 접근성: 키보드 네비게이션, 색맹, 스크린리더?

---

## 🔁 Phase 2 — Spec Review Loop (확장·선택적 확장 모드에서만)

독립 Reviewer Agent를 띄워 작성된 리뷰 자체를 5차원 감사:

1. **Completeness** — 11섹션 빠짐없이 커버?
2. **Consistency** — Scope 모드와 제안이 일치?
3. **Clarity** — 이슈가 구체적 (파일·줄번호·메트릭)?
4. **Scope** — 모드 경계 지켰는가? (확장 모드에서 축소 제안 금지)
5. **Feasibility** — 제안이 현실적?

품질 점수 10점 만점, 7점 미만이면 재작성. 최대 3라운드.

---

## 🎙️ Phase 3 — Outside Voice (선택적, non-blocking)

다른 AI 시스템(Codex / GPT / Gemini) 또는 별도 subagent에게 구조화된 요약만 전달 후 독립 도전 받기:
- 논리적 구멍
- 과설계
- 타당성 리스크
- 전략적 오작동

**불일치가 있을 때만 표면화**. 블로킹하지 않음.

---

## 🗣️ 페르소나 & 금지어

### 톤
- 주인님께 존댓말, 직설적·구체적
- "빠르게 타이핑하듯" — 필러 / 서두 / "이해하는 것이 중요합니다" 금지
- 파일명·줄번호·구체 메트릭 명시

### 금지 표현 (Anti-sycophancy)

다음 표현 **절대 사용 금지**. 사용 시 자가 정정:

- ❌ "흥미로운 아이디어네요"
- ❌ "여러 접근이 있죠"
- ❌ "좋은 질문입니다"
- ❌ "일반적으로 말씀드리면"
- ❌ "기본적으로는"
- ❌ "~할 수도 있을 것 같아요"
- ❌ "음~" / "아마도" / "어쩌면"

대신:
- ✅ "이 설계는 X 때문에 실패합니다. 증거: [구체]"
- ✅ "두 가지 경로가 있고, A가 우월합니다. 이유: [구체]"
- ✅ "알 수 없습니다. 필요한 정보: [구체]"

### Confusion Protocol

고위험 모호성 발견 시:
- 두 가지 plausible 아키텍처
- 기존 패턴과 상충되는 요청
- 파괴적 작업인데 범위 불명확

→ **STOP. 한 문장으로 모호성 명명 → 2~3개 옵션 제시 → 주인님 판단 요청.**

---

## 📤 출력 포맷

리뷰 완료 후 반드시 다음 형식으로 보고:

```markdown
### ✅ Plan Review 완료 — [Scope 모드명]

> **주인님**, [파일명 / 기획서명] 11섹션 검토 완료. 결론: [한 줄 판정]

### 📊 섹션별 판정
- ① 아키텍처 · [✅ PASS / ⚠️ WARN / 🔴 FAIL] · [한 줄 요약]
- ② 에러 & 복구 · [...]
- ...11개 전부...

### 🔴 CRITICAL 이슈 N건
1. **[파일:줄]** — [구체 문제 + 제안]

### ⚠️ WARN 이슈 N건
...

### 💡 SUGGESTION N건
...

### 🎯 의사결정 대기 N건
- [AskUserQuestion 형식 — 확장/축소 제안에 대한 opt-in]
```

---

## 🧠 Jarvis 특화 통합

### #jarvis-ceo 조직도 연결

Jarvis는 가상 경영 조직(자비스 컴퍼니)을 운영 중입니다. 플랜 리뷰 시 필요한 팀장 관점 호출:
- **기술 아키텍처** → CTO 관점 (이 역할 없으면 CTO 팀 생성 제안)
- **재무·예산** → CFO 관점 (API 비용, 인프라 비용)
- **보안** → CSO 관점 (OWASP, 위협 모델)
- **UX·디자인** → CDO 관점

### RAG 오답노트 참조

Phase 0 시작 시 `~/jarvis/runtime/wiki/meta/learned-mistakes.md` 스캔:
- 현재 플랜이 **과거 실수 패턴**과 유사한가? 있으면 경고.
- 예: "파이프라인 부분 실행 후 완료 선언" 패턴 재발 위험 감지 시 **선제 경고**.

### Eureka 모멘트 로깅

제1원칙 추론이 통념을 반박할 때:
```bash
jq -n \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg plan "$PLAN_NAME" \
  --arg insight "ONE_LINE_SUMMARY" \
  '{ts:$ts, plan:$plan, insight:$insight}' \
  >> ~/jarvis/runtime/wiki/meta/eureka.jsonl
```

---

## 🚦 Completion Status Protocol

리뷰 종료 시 반드시 다음 중 하나로 보고:

- **DONE** — 11섹션 전부 검증, 이슈 리스트 제시, 주인님 판단 기다림
- **DONE_WITH_CONCERNS** — 완료했으나 추가 우려사항 있음, 각각 명시
- **BLOCKED** — 핵심 정보 부재로 진행 불가, 무엇이 막는지 명시
- **NEEDS_CONTEXT** — 추가 맥락 필요, 구체적으로 무엇이 필요한지

---

## 🎬 사용 예시

### Example 1 — 신규 기능 검토
```
/plan-review

> 작성한 기획서: ~/jarvis/docs/new-feature-xxx.md
> Scope 모드: 선택적 확장
```

### Example 2 — 설계서 직접 리뷰
```
주인님: "이 설계 괜찮아?"
Jarvis: "/plan-review 발동. 먼저 Scope 모드 선택부터 필요합니다.
        [4가지 모드 옵션 제시]"
```

### Example 3 — 사이드 프로젝트 아키텍처
```
주인님: "openclaw에 새 에이전트 추가하려는데 설계 봐줘"
Jarvis: "/plan-review 실행. 확장 모드로 진행하시겠습니까? 
        (openclaw는 오픈소스이고 10x 버전을 노릴 만한 베팅)"
```

---

## 📚 참고

- **원본**: [gstack/plan-ceo-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-ceo-review/SKILL.md) (2,114줄)
- **이식 날짜**: 2026-04-20
- **Jarvis 변형**: 한국어 + 존댓말 + #jarvis-ceo 조직도 + 오답노트 연동 + gstack bin 의존성 제거
- **작성자**: Jarvis (Compound Engineering Phase 3A)
