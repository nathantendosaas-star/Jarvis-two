---
description: "체계적 근본원인 추적(5 Why + 원인 체인). 크론 실패, 장애, 재현 버그 디버깅. '디버깅', '근본 원인', 'investigate', '왜 실패했어' 요청 시 사용."
---

# Investigate — 5 Why 근본 원인 체인 추적

이 커맨드는 gstack의 `/investigate`를 Jarvis 페르소나·한국어 환경에 맞춰 이식한 것입니다.
**목적은 증상 억제가 아니라 근본 원인(root cause) 발견**입니다.

---

## 🎯 발동 조건

- 크론 작업 실패, LaunchAgent 비정상 종료, 봇 무응답 등 장애
- 재현 가능한 버그의 원인 추적
- "왜 실패했어?" / "근본 원인이 뭐야?" / "investigate" 요청

---

## 🧭 기존 Jarvis 도구와의 역할 구분

세 스킬은 **상호 보완** 관계입니다. 혼동 금지.

- **`doctor`** (증상 레벨) — "지금 다 정상이야?"
- **`/investigate`** (원인 레벨) — "왜 실패했지?"
- **`crisis`** (조치 레벨) — "봇 죽었어, 일단 살려"

**흐름 예**: `crisis`로 지혈 → `/investigate`로 원인 추적 → `doctor`로 정기 점검.

---

## 🏛️ Iron Law

> **근본 원인 확인 없이 수정 금지 (NO FIXES WITHOUT ROOT CAUSE).**

증상만 고치는 수정은 다음 버그를 더 찾기 어렵게 만듭니다.

---

## 🔗 Phase 0 — 사전 조사

### 0.1 auto-diagnose 결과 수집

```bash
if [ -x ~/jarvis/scripts/auto-diagnose.sh ]; then
  ~/jarvis/scripts/auto-diagnose.sh --json > /tmp/investigate-symptoms.json
fi
```

이 결과는 **증상 스냅샷**입니다. 이 스킬의 역할은 **원인 체인**을 찾는 것.

### 0.2 오답노트 스캔

```bash
if [ -f ~/jarvis/runtime/wiki/meta/learned-mistakes.md ]; then
  grep -A 3 -i "$KEYWORD" ~/jarvis/runtime/wiki/meta/learned-mistakes.md || true
fi
```

과거 패턴 매칭 시 주인님께 즉시 보고: "이전 학습된 실수 패턴과 유사합니다. 파일: [경로], 발생일: [날짜]."

---

## 📋 Phase 1 — 근본 원인 조사

### 1.1 증상 수집
- 에러 메시지, 스택 트레이스, 재현 절차 전문 확보
- AskUserQuestion으로 **한 번에 하나씩** 질문
- 로그: `~/.jarvis/logs/`, `~/Library/Logs/jarvis/`

### 1.2 코드 경로 추적
- Grep으로 증상 발생 지점부터 역방향 추적
- Read로 각 호출 지점 로직 확인
- **전체 파일 읽기 금지** — Serena MCP 활용

### 1.3 최근 변경 확인 (회귀)

```bash
git log --oneline -20 -- <파일>
git diff HEAD~5 -- <파일>
```

이전에 동작했다면 **회귀(regression)**. 근본 원인은 diff 안에 있습니다.

### 1.4 결정론적 재현

- 타이밍 의존 → 경쟁 상태
- 환경 의존 → 환경 변수 / DB 상태 / 캐시
- **재현 불가 버그에 추측 수정 금지.** 로깅 추가 → 다음 발생 대기.

### 1.5 5 Why 체인

```
증상: 크론 작업 실패 (exit 1)
  └─ 왜? 스크립트 내 source 명령 실패
    └─ 왜? 설정 파일이 없음
      └─ 왜? launchd가 cwd를 $HOME로 설정
        └─ 왜? plist에 WorkingDirectory 누락
          └─ 왜? 초기 작성 시 체크리스트 없었음 ← 구조적 근본 원인
```

**5단계 도달 전 멈추지 마십시오.** 3단계에서 멈추면 증상 수정.

---

## 🧪 Phase 2 — 패턴 매칭

알려진 패턴:
- **경쟁 상태**: 간헐적, 타이밍 의존, 공유 상태 동시 접근
- **Null 전파**: NoneType, TypeError, 옵셔널 가드 누락
- **상태 손상**: 부분 업데이트, 트랜잭션, 콜백
- **통합 실패**: 타임아웃, 외부 API, 서비스 경계
- **설정 드리프트**: 로컬 OK, 프로덕션 실패, env vars / DB 상태
- **캐시 오염**: 오래된 데이터, Redis / CDN / 브라우저

**같은 영역 반복 버그는 아키텍처 냄새(architectural smell)**입니다. 우연 아님.

---

## ⚗️ Phase 3 — 가설 검증

### 3.1 가설 확인
임시 로그·단언문·디버그 출력 추가 → 재현 → 증거 일치.

### 3.2 가설 실패 시
다음 가설 세우기 **전에** 증거 더 수집. 추측 금지.

### 3.3 3-Strike 룰

3개 가설 모두 틀리면 **반드시 STOP**. AskUserQuestion:

```
가설 3회 실패. 아키텍처 이슈 가능성.

A) 조사 계속 — 새 가설: [설명]
B) 에스컬레이션 — 시스템 아는 사람의 도움
C) 로깅 추가 후 대기 — 계측 완료 후 다음 발생 포착
```

### 🚩 위험 신호

- "일단 급한 불만 끄자" → 금지. 제대로 고치거나 에스컬레이션.
- 데이터 흐름 추적 전 수정안 제시 → 추측.
- 수정 하나가 다른 문제 발생 → 레이어를 잘못 짚은 것.

---

## 🔧 Phase 4 — 구현

### 4.1 최소 변경
실제 문제 제거하는 **최소 diff**. 리팩토링 충동 억제.

### 4.2 Blast Radius 경고 (5개 초과)

```
이 수정은 N개 파일에 영향. 버그 수정치고 범위가 큽니다.
A) 진행 — 근본 원인이 실제로 이 파일들에 걸쳐 있음
B) 분리 — 핵심 경로만 지금 수정
C) 재고 — 더 타겟된 접근
```

### 4.3 회귀 테스트

- **수정 없이 실패**하는 테스트
- **수정 후 성공**하는 테스트

### 4.4 전체 테스트 실행

```bash
pytest / jest / cargo test / go test ./...
```

---

## ✅ Phase 5 — 검증 & 보고

### 5.1 프레시 검증
원래 버그 시나리오 **처음부터** 재현. 선택 사항 아닙니다.

### 5.2 구조화 리포트

```
DEBUG REPORT — /investigate
증상 (Symptom)     : [관찰 현상]
5 Why 체인         : [1 → 2 → … → 근본]
근본 원인 (Root)    : [실제로 무엇이 틀렸는가]
수정 (Fix)         : [변경 + 파일:줄]
증거 (Evidence)    : [테스트 출력]
회귀 테스트         : [새 테스트 파일:줄]
연관 (Related)     : [오답노트, 과거 버그]
상태 (Status)      : DONE | DONE_WITH_CONCERNS | BLOCKED
```

---

## 🧠 Jarvis 특화 통합 (3가지)

### 1. 오답노트 등록

```bash
cat >> ~/jarvis/runtime/wiki/meta/learned-mistakes.md <<EOF

## $(date +%Y-%m-%d) — [한 줄 제목]

- 증상: [요약]
- 근본 원인: [5 Why 최종]
- 수정: [파일:줄]
- 재발 방지: [구조적 가드 / 체크리스트]
- 연관 커밋: $(git rev-parse --short HEAD)

EOF
```

### 2. auto-diagnose 연계

- doctor가 "크론 2개 실패" → /investigate가 "둘 다 설정 누락이 원인"
- 증상 여러 개 → 공통 근본 원인 1개 가능성. 교차 확인.

### 3. Eureka 로깅

```bash
if [ -n "$EUREKA_INSIGHT" ]; then
  jq -n \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg bug "$BUG_SUMMARY" \
    --arg insight "$EUREKA_INSIGHT" \
    --arg files "$AFFECTED_FILES" \
    '{ts:$ts, bug:$bug, eureka:$insight, files:$files, skill:"investigate"}' \
    >> ~/jarvis/runtime/wiki/meta/eureka.jsonl
fi
```

예: "launchd의 cwd가 `/`가 아닌 `$HOME`" / "Discord 봇의 SIGTERM이 사실 OOM killer".

---

## 🗣️ 페르소나 & 금지어

### 톤
- 주인님께 존댓말. 냉철·간결·구체.
- 파일명·줄번호·로그 발췌·명령어 출력 명시.

### 금지 표현

- ❌ "이걸로 고쳐질 것 같아요" → ✅ "테스트 실행 후 고쳐짐 확인. 출력: [전문]"
- ❌ "아마 이게 원인일 겁니다" → ✅ "가설 A — 근거: [파일:줄]. 검증: [구체]"
- ❌ "급한 대로 이렇게" → ✅ "이 수정은 증상만 억제. 근본 원인은 [X]. 별도 작업 필요."

---

## 🚦 Completion Status Protocol

- DONE — 근본 원인 확인, 수정 적용, 회귀 테스트, 전체 테스트 통과
- DONE_WITH_CONCERNS — 수정했으나 완전 검증 불가
- BLOCKED — 조사 후에도 근본 원인 불명확

### 에스컬레이션 양식

```
STATUS: BLOCKED | NEEDS_CONTEXT
REASON: [1~2 문장]
ATTEMPTED: [시도한 가설 3개와 실패 이유]
RECOMMENDATION: [주인님이 다음에 할 일]
```

---

## ⚠️ 중요 규칙

- **3회 수정 실패 → STOP 후 아키텍처 재검토.**
- **검증 불가 수정 절대 배포 금지.**
- **"이걸로 될 겁니다" 금지.** 테스트로 증명.
- **5개 파일 초과 → AskUserQuestion blast radius 경고.**
- **오답노트 업데이트 누락 금지** — Phase 5 필수.

---

## 🎬 사용 예시

### 예 1 — 크론 실패

```
주인님: "tqqq 크론이 어젯밤에 실패했어. 왜?"
Jarvis: "/investigate 발동. Phase 0:
        1. auto-diagnose 수집 중...
        2. learned-mistakes 스캔 중... 과거 유사 패턴 발견 (2026-03-12)
        3. journalctl 로그 확인 중..."
```

### 예 2 — 봇 무응답

```
주인님: "Discord 봇이 메시지 씹어. 디버깅해줘"
Jarvis: "/investigate. 재현 가능성 먼저 확인 필요.
        - 특정 채널만인지, 전체인지?
        - 재시작 후에도 재현?
        [AskUserQuestion 1건씩]"
```

---

## 📚 참고

- 원본: gstack `/investigate` (1,037줄)
- 이식 날짜: 2026-04-20 KST
- Jarvis 변형: 한국어 + 존댓말 + 오답노트 연동 + auto-diagnose 연계 + eureka 로깅 + gstack bin 제거
- 자매 스킬: `doctor`(증상) · `crisis`(조치)

---

## 🏢 조직도·결재 연계

본 스킬은 **자비스 컴퍼니** 조직도 상 **비서실장(Sonnet)** 주관으로 실행되며, 결재 레벨은 다음과 같습니다.

- **L1 (자율실행)**: 로그·증거 수집, 5 Why 질문 생성, 타임라인 재구성
- **L2 (실행 후 보고)**: 의심 구간 수정안 드래프트, 추가 관측 지표(메트릭·알림) 제안
- **L3 (비서실장 승인)**: 프로덕션 데이터 접근이 필요한 실증 실험, 코드 변경 적용
- **L4 (주인님 결재)**: 데이터 롤백·삭제, 프로덕션 장애 강제 재현, 보안 사고 공시
- **CEO(Opus) 에스컬레이션**: 동일 근본원인이 3회 이상 재발하거나 단일 컴포넌트가 아닌 아키텍처 수준 재설계가 필요하다고 판단될 때

## 📚 Compound Engineering 훅

본 스킬의 산출물은 Jarvis 학습 자산 3종과 자동 연결됩니다.

- **Eureka** (`~/jarvis/runtime/wiki/meta/eureka.jsonl`) — 재사용 가능한 패턴·인사이트 저장 (`/learn` 스킬 주관)
- **오답노트** (`~/jarvis/runtime/wiki/meta/learned-mistakes.md`) — 실패 패턴 → 대응 4필드(패턴/실제/증거/대응) 누적
- **회고 리포트** (`/retro` 산출물 `~/jarvis/runtime/state/retro/`) — 블레임리스 구조 개선안

세 파일은 다음 `/autoplan` Phase 0(선제 조회)에서 자동으로 검색되어 **같은 실수를 반복하지 않도록** 보장합니다. 본 스킬 실행 중 재사용 가능한 통찰이나 실패 사례를 발견하면 즉시 `/learn` 호출을 권고합니다.
