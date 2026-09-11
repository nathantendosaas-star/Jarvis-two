---
description: "코드 리뷰. Dev+Reviewer 에이전트로 코드 품질 검토. '코드 리뷰', '리뷰 해줘', '코드 검토', 'review' 요청 시 사용."
---

# 코드 리뷰 (Dev + Reviewer Agent)

현재 작업한 코드를 Reviewer 관점에서 검토합니다.

## 리뷰 프로세스

```
코드 확인 → 체크리스트 검토 → 이슈 리포트 → 수정 → 재검토
```

---

## 1단계: 변경 사항 파악

```bash
# 스테이징된 변경
git diff --cached --stat

# 전체 변경
git diff --stat

# 최근 커밋 (아직 안 커밋했다면 스킵)
git log --oneline -5
```

변경된 모든 파일을 읽고 분석합니다.

---

## 2단계: 리뷰 체크리스트

### 일반 코드 품질

| # | 항목 | 확인 |
|---|------|------|
| 1 | 로직 오류 없는가 | |
| 2 | 엣지케이스 처리했는가 | |
| 3 | null/undefined 안전한가 | |
| 4 | 에러 핸들링 적절한가 | |
| 5 | SSoT(Single Source of Truth) 위반 없는가 | |
| 6 | DRY(Don't Repeat Yourself) 위반 없는가 | |
| 7 | 명명 규칙 일관적인가 | |
| 8 | 불필요한 코드/주석 없는가 | |
| 9 | 보안 취약점 없는가 (OWASP Top 10) | |
| 10 | 하드코딩된 비밀값 없는가 | |

### Shell Script 특화

| # | 항목 | 확인 |
|---|------|------|
| 1 | `set -euo pipefail` 설정했는가 | |
| 2 | 변수 따옴표 처리 (`"$var"`) | |
| 3 | 임시 파일 cleanup (trap) | |
| 4 | 경로에 공백 대응 | |
| 5 | exit code 적절한가 | |

### OpenClaw 특화

| # | 항목 | 확인 |
|---|------|------|
| 1 | watchdog 안전성: 무한루프 가능성 없는가 | |
| 2 | Gateway 재시작 시 Grace Period (30초) 준수하는가 | |
| 3 | launchd plist: KeepAlive/RunAtLoad 설정 적절한가 | |
| 4 | 토큰 동기화: openclaw.json과 plist 간 불일치 없는가 | |
| 5 | 로그 경로: ~/.openclaw/logs/ 사용하는가 | |
| 6 | Discord 알림: 연속 실패 임계치(3회) 준수하는가 | |
| 7 | jq: `has()` 키 검사 사용 (null 매칭 버그 방지) | |
| 8 | 크론/LaunchAgent 중복 없는가 | |

---

## 3단계: 이슈 리포트

발견된 이슈를 심각도별로 분류합니다:

```
## Review Report

### CRITICAL (즉시 수정 필요)
- [파일:줄번호] 설명

### WARNING (수정 권장)
- [파일:줄번호] 설명

### SUGGESTION (개선 제안)
- [파일:줄번호] 설명

### PASS
- 전체적으로 양호한 부분 요약
```

---

## 4단계: 수정 후 재검토

CRITICAL/WARNING 항목을 수정한 후 재검토합니다:
1. 수정된 파일 다시 읽기
2. 해당 이슈가 해결되었는지 확인
3. 새로운 이슈가 발생하지 않았는지 확인
4. 최종 리포트 출력

---

## 실행 방법

1. **전체 리뷰**: "/review" 실행
2. **특정 파일**: "/review [파일경로]"
3. **최근 커밋**: "/review --last-commit"
4. **리뷰 후 자동 수정**: "/review --fix"

## 참고 문서
- CLAUDE.md: 코딩 정책 및 컨벤션
- ~/openclaw/docs/self-healing-system.md: watchdog/gateway 아키텍처
- ~/.claude/commands/sdd.md: 스펙 주도 개발 가이드
