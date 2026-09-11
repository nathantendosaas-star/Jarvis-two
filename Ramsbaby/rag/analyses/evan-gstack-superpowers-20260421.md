---
source: youtube
video_id: af3OJ0L1jEU
title: GStack + Superpowers로 클로드코드 완전히 달라진 사람의 후기
uploader: 메이커 에반
upload_date: 2026-04-15
duration_sec: 547
analyzed_at: 2026-04-21T14:35:00+09:00
analysts: 6-agent parallel team (transcript / visual-early / visual-late / jarvis-audit / harness-patterns / roadmap)
verify_report: ~/jarvis/runtime/logs/verify/verify-20260421-142854.log
commercial_check: clean (no ad/sponsor/coupon in transcript)
---

# 영상 분석 아카이브 — GStack + Superpowers

## 요약

에반은 클로드 코드 플러그인을 **2개만 남기고 다 지웠다**: **GStack**(Office Hours + Design Review) + **Superpowers**(Sub-agent Driven Dev + Git Worktrees + 자동 기록 + Writing Plans + Brainstorming). 영상은 100% 모션그래픽이며 CLI 데모·설치 스크린샷은 GitHub README로 위임. 상업 협찬 없음.

## Jarvis 기능 매트릭스 (4분류: 동일/부분/부재/역전)

| 영상 기능 | Jarvis 자산 | 평가 | 근거 |
|---|---|---|---|
| Office Hours (**아이디어 인터뷰**) | `/office-hours` (의사결정 면담) | **🔴 부재** | 이름만 같고 기능 완전 다름 — 전자는 발산, 후자는 수렴. 신규 `/brainstorm` 필요 |
| Design Review (AI slop 감식) | `discord-visualization.md` 룰 | **🟡 부분** | 생산 전 금지 룰만. 생산 후 감식 에이전트 부재. 신규 `/design-review` 필요 |
| Sub-agent Driven Dev | `/orchestrate` (3-agent) | **🟡 부분** | Research/Code/Validation vs 영상 기획/디자인/개발/QA. Designer 역할 누락 |
| Git Worktrees 격리 | 실운영 17개 활성 | **🟢 동일** | 실증 확인 |
| 자동 기록 | Stop 훅 9개 체인 (오답노트 포함) | **🟣 역전** | Jarvis가 초과 달성 (ledger · RAG · wiki · changelog 4중) |
| Writing Plans | `/autoplan` | **🟢 동일** | 계획 분해 + 자기 정박 메커니즘 확인 |
| Plan + Review 이중 검증 | `/plan-review` + `/verify` | **🟣 역전** | 7-Gate + Contrarian Challenge로 영상보다 강함 |
| Brainstorming (UI mockup 각도) | 없음 | **🔴 부재** | Superpowers 고유 기능 — `/brainstorm` Phase 3에 이식 |
| 고정 순서 파이프라인 | 암묵적 | **🔴 부재** | Golden Path 명시 필요 (CLAUDE.md 추가 완료) |

**정리**: 🔴 4건 부재(신규 이식) / 🟡 2건 부분(보강) / 🟢 2건 동일 / 🟣 2건 역전 (Jarvis 우위).

## 명시적 하네스 패턴 (6)

1. **즉시 생성 금지** — Office Hours 선상담 → 요구사항 공백 강제 노출
2. **AI Slop 사후 감식관** — 생산 ≠ 검사 분리
3. **Sub-agent 역할 분할** — 기획·디자인·개발·QA 별 컨텍스트
4. **Writing Plans 자기 정박** — 계획서가 드리프트 방지 앵커
5. **Plan + Review 이중 검증** — 작성자 ≠ 검토자
6. **고정 순서 강제 파이프라인** — 스킵 불가

## 암시적 패턴 (4)

1. **Worktrees = 블라스트 반경 물리 격리**
2. **자동 커밋 체크포인트 = 망각 방지 원장** (의미 단위)
3. **Mockup-First, Figma-Less 디렉팅**
4. **툴 미니멀리즘** — 플러그인 증식은 프롬프트 오염원

## 안티 권고 (이식 금지)

1. **팀 모드 자동 사냥** — 에반 본인도 거부. Jarvis Iron Law 3 (User Sovereignty) 직충돌. 2026-04-20 repo private 전환 사고의 재발 경로
2. **기계적 플러그인 최소화** — Jarvis 스케일에 부적합. SSoT·DRY는 "중복 금지"지 "개수 상한" 아님

## Verify Agent 지적 (58/100 CONDITIONAL PASS)

- 🔴 `/office-hours` 허위 등가 — 이름만 같고 기능 다름 (자기편향)
- ⚠️ 숫자 오차: worktree 16(주장) / 17(실측), 스킬 35(실측) — 6일 갭 간 변동 가능성
- ⚠️ 초기 Phase 1에 회귀·롤백·관측 계획 제로
- ⚠️ CLAUDE.md SSoT 미지정 (3경로 존재)
- ⚠️ "Jarvis가 더 강하다" 분모·분자 정의 없이 사용

**정정 반영**: 본 매트릭스는 verify 지적 반영 후 재작성. `/brainstorm` 분리, `/design-review` 철학 충돌 해소, SSoT 확정.

## Phase 1 산출물 (커밋 대상)

1. `~/.claude/commands/brainstorm.md` — 신규 스킬
2. `~/.claude/commands/design-review.md` — 신규 스킬
3. `~/jarvis/CLAUDE.md` Golden Path 섹션 — 본 문서와 동기

## 원자료 경로

- Transcript: `/tmp/_evan_video/transcript.txt` (310줄, 16.7KB)
- 원본 VTT: `/tmp/_evan_video/af3OJ0L1jEU.ko.vtt`
- 프레임: `/tmp/_evan_video/frame_0001.jpg ~ frame_0274.jpg` (274장, 2초 간격)
- 비디오: `/tmp/_evan_video/af3OJ0L1jEU.webm` (11MB)

참고: `/tmp`는 OS 재부팅 시 휘발. 영구 보존 필요 시 `~/jarvis/rag/analyses/raw/` 이관 검토.

## Next Actions (후속)

- Phase 2 (1주 내): `/orchestrate` v2에 Designer 역할 추가 — 기획·디자인·개발·QA 4축
- Phase 3 (장기): 자비스맵에 design-review 노드 시각 통합
- 모니터링: 유사도 임계값 0.4(오늘 하향) 가 한 주 운영 후 적절한지 재평가
