---
description: "생산 후 AI slop 감식관 — 완성된 HTML·SVG·이미지·Discord 카드·이력서·블로그·자비스맵 UI에서 AI 티 나는 요소(진부한 폰트·그라데이션·둥근8px+그림자·이모지 남발)를 탐지해 수정안과 함께 보고. '디자인 리뷰', 'design review', 'AI slop 체크', '시각 감사', 'slop 있어?' 요청 시 사용. /review(코드 리뷰)와 다름 — 이건 시각 산출물 전용."
---

# /design-review — AI Slop 감식관

> **한 줄**: 만든 뒤 눈으로 봤을 때 "AI가 만들었네" 라는 인상을 주는 진부한 요소를 **생산 후 자동 감식**.

## /review와의 경계 (혼동 금지)

| 스킬 | 대상 | 방법 |
|---|---|---|
| `/review` | 코드 로직·버그·스타일 | Dev+Reviewer 에이전트 |
| `/design-review` | 시각 산출물 (HTML·CSS·SVG·이미지) | 체크리스트 기반 감식 |
| `discord-visualization.md` (룰) | **생산 전** 금지 가이드 | 정적 룰 |

**보완 관계**: `discord-visualization.md`는 "만들 때 쓰지 마"는 룰, `/design-review`는 "다 만든 뒤 남았는지 검사"하는 감식관. 충돌 아닌 이중 방어.

## 언제 사용합니까

- `/my-resume` 생성 직후
- `/blog-writer` 초안 완료 후
- 자비스맵(jarvis-board) 컴포넌트 추가 후
- HTML 리포트 / 슬라이드 / 디스코드 카드 / SVG 다이어그램 작성 직후
- 주인님이 "AI 티 나?", "디자인 어때?" 하시는 순간

## 입력

세 가지 중 하나:
1. **파일 경로** — `.html`, `.svg`, `.css`, `.md`(마크다운 프레이밍 포함), `.tsx/.jsx`(Styled Component·Tailwind)
2. **스크린샷** — `.png`, `.jpg`, `.webp` (이미지 Read 후 시각 분석)
3. **URL** — `localhost:3000`류 개발 서버 → chrome MCP로 렌더 캡처 후 분석 (MCP 가용 시)

## 감식 체크리스트 (5 카테고리 × 4 항목 = 20점)

### A. 서체 (Typography) — 4점
- `[A1]` Inter / Roboto / Arial 등 **진부한 산세리프 기본값** 사용 감지
- `[A2]` 헤딩·본문 모두 동일 서체만 사용 (대비 없음)
- `[A3]` `font-family` 명시 없이 브라우저 기본값 의존
- `[A4]` 한국어 콘텐츠인데 영문 전용 서체만 스펙

### B. 색상 (Color) — 4점
- `[B1]` **흰 배경 + 보라 그라데이션** 조합 (AI 슬롭 1호)
- `[B2]` **푸른색 그라데이션** 대시보드 헤더
- `[B3]` 악센트 색상이 #FF0000, #00FF00 같은 원색
- `[B4]` 다크 모드 배경이 순흑 `#000000` (대비 과잉)

### C. 레이아웃 (Layout) — 4점
- `[C1]` 좌우 50:50 카드 **반복** (3섹션 이상 동일 패턴)
- `[C2]` 12-column grid 무비판 사용 (콘텐츠 구조 무관)
- `[C3]` 모든 컨테이너 `max-width: 1200px` 중앙 정렬 동일
- `[C4]` 헤더·사이드바·푸터 3분할 템플릿 그대로

### D. 컴포넌트 (Component) — 4점
- `[D1]` **둥근 모서리 8px + 박스 그림자 + 호버 lift** 3종 세트 남발
- `[D2]` 버튼 모두 동일 스타일 (primary/secondary 구분 없음)
- `[D3]` 아이콘이 모두 outline heroicons 기본
- `[D4]` 카드 패딩·간격 모두 `16px`·`24px` 정박

### E. 콘텐츠 (Content) — 4점
- `[E1]` 이모지 남발 (한 섹션 3개 이상) — 단, 주인님 CLAUDE.md는 CLI 출력 이모지 허용 (맥락 판단)
- `[E2]` **"혁신적", "놀라운", "차세대"** 같은 공허한 수식어
- `[E3]` 플레이스홀더 텍스트(`Lorem ipsum`, `Sample text`)가 프로덕션에 남음
- `[E4]` 숫자 다 `0` 또는 `100`으로 하드코딩된 차트 (실데이터 미반영)

## 실행 프로토콜

### Phase 1 — 입력 식별 + 카테고리 확정

```bash
# 파일 경로 입력 시
file "$INPUT"  # 타입 확인
```

카테고리 결정 (`~/.claude/rules/discord-visualization.md` 매핑 표 재사용):
- 편집·포트폴리오 (이력서·블로그·HTML 리포트) → 크림/세리프/테라코타 기대
- 데이터앱 (디스코드 카드·대시보드) → 다크/차분한 회색 기대
- 개발툴 (자비스맵) → 다크/slate/indigo 기대

### Phase 2 — 20 체크리스트 스캔

각 항목을 순서대로:
- `[FOUND]` or `[OK]` 판정
- FOUND면 증거 인용 (라인 번호 · 선택자 · 값)
- 심각도: `CRITICAL`(AI 슬롭 4금 직격) / `WARNING`(개선 권장) / `MINOR`

### Phase 3 — 점수 + 판정

- 20점 만점에 FOUND 개수 차감
- `18~20점`: ✅ **Clean** (AI 티 거의 없음)
- `14~17점`: 🟡 **Acceptable** (권장 수정 있음)
- `10~13점`: 🟠 **Needs Revision**
- `<10점`: 🔴 **Heavy Slop** (재작성 권고)

### Phase 4 — 수정안 제시 (FOUND마다)

각 발견마다:
- **현재**: `.hero { background: linear-gradient(#fff, #a855f7) }`
- **권장**: `.hero { background: #F4F1EA; accent: #D4622A }`
- **근거**: discord-visualization.md 카테고리 "편집·포트폴리오" 팔레트
- **Iron Law 체크**: 수정이 다른 원칙(페르소나·SSoT) 침해하는지 확인

### Phase 5 — 보고 포맷

```
## 🎨 Design Review — <파일명> (YYYY-MM-DD HH:MM KST)

**점수**: 16/20 🟡 Acceptable
**카테고리**: 편집·포트폴리오

### 🔴 CRITICAL (N건)
1. [B1] 흰 배경 보라 그라데이션 — `hero.css:12`
   - 현재: `linear-gradient(white, #a855f7)`
   - 권장: `#F4F1EA`
   - 근거: discord-visualization.md 편집·포트폴리오 매핑

### 🟡 WARNING (M건)
2. [D1] 8px + 그림자 + 호버 3종 세트 — `card.css:45`
   ...

### ✅ Clean (남은 K개 체크)

### 🎯 Next Actions
1. ...
```

## 원칙

- **증거 없이 판정 금지** — 모든 FOUND는 파일 경로·라인 또는 픽셀 좌표 인용
- **추측 금지** — 흐릿한 이미지는 "불분명 — 파일 경로로 재분석 권장"
- **주인님 결재**: 수정 자동 적용 금지. 권고만, 실행은 /codex·/ship으로 위임
- **페르소나**: 한국어 존댓말, 주인님 호칭 유지
- **AI slop 체크리스트는 `discord-visualization.md`의 SSoT와 동기**: 룰 업데이트 시 이 스킬도 함께 업데이트 필수

## 롤백

- 신규 스킬이므로 부작용 0. `rm ~/.claude/commands/design-review.md`
- `discord-visualization.md` 룰 자체는 무변경

## 회귀 테스트

- `/review` 트리거 키워드(`"코드 리뷰 해줘"`)에 이 스킬이 간섭하지 않는지 확인
- 기존 my-resume·blog-writer·자비스맵 렌더링 동작에 영향 없음 (읽기 전용)

## 관측

- 스킬 호출 시 stdout 점수를 `~/jarvis/runtime/state/design-review-ledger.jsonl`에 한 줄 append (선택, Phase 2에서 보강)
- 반복 FOUND 패턴이 있으면 주간 감사가 자동으로 `learned-mistakes.md` 등재

## 참조

- 룰 SSoT: `~/.claude/rules/discord-visualization.md` (🎨 시각 출력 디자인 정책)
- 원본 영감: 2026-04-15 메이커 에반 유튜브 "GStack Design Review"
- 관련 스킬: `/brainstorm` (생산 전 UI 방향 제안), `/review` (코드 리뷰), `/my-resume`, `/blog-writer`
