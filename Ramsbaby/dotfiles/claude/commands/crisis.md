---
description: "긴급 상황 대응. 서비스 중단, 봇 다운, 크리티컬 버그, 장애 대응 프로세스. '긴급', '장애 대응', 'crisis', '봇이 죽었어', '서비스 멈췄어' 요청 시 사용."
---

# 긴급 상황 대응 (Crisis Response)

서비스 중단/외부 의존성 변경/크리티컬 버그 등 긴급 상황 대응 프로세스를 시작합니다.

## 1단계: 상황 파악 (5분 내)

```bash
# 현재 시스템 상태 빠른 확인
openclaw status
launchctl list | grep ai.openclaw
tail -50 ~/.openclaw/logs/watchdog.log
tail -50 ~/.openclaw/logs/gateway.log
```

**파악 항목**:
- [ ] 어떤 서비스가 영향받는가?
- [ ] 언제부터 발생했는가?
- [ ] 외부 의존성 변경인가 vs 내부 버그인가?
- [ ] 유저 영향 범위는?

## 2단계: 리포트 작성 (에이전트 간 통신 패턴)

`/tmp/crisis-report.md` 파일로 상황 공유:

```markdown
# Crisis Report - [날짜 시간]

## 상황
- 증상: ...
- 발생 시각: ...
- 영향 범위: ...

## 시도한 것
- [ ] 서비스 재시작
- [ ] 로그 확인
- [ ] ...

## 필요한 것
- 백엔드에서 필요한 정보: ...
- 예상 해결책: ...
```

## 3단계: 격리 & 즉시 대응

```bash
# 문제 서비스 격리
launchctl stop ai.openclaw.gateway

# 로그 상세 캡처
journalctl -u ai.openclaw 2>/dev/null || \
  cat ~/.openclaw/logs/*.log | tail -200 > /tmp/crisis-logs.txt

# 백업 (수정 전 필수)
cp -r ~/openclaw ~/openclaw.crisis-backup-$(date +%Y%m%d-%H%M%S)
```

## 4단계: 해결 체크리스트

### 외부 의존성 변경 시 (책: 콩콩프렌즈 사례 - 3일 내 해결)
- [ ] 의존성 완전 제거 or 자체 구현 결정
- [ ] 최소 동작 버전 먼저 구현 (MVP)
- [ ] E2E 테스트로 검증
- [ ] 배포 후 24시간 모니터링

### 내부 버그 시
- [ ] 원인 코드 격리 (최소 재현 케이스)
- [ ] `.bak` 백업 후 수정
- [ ] `/review` 스킬로 코드 검토
- [ ] 단계적 배포

### Gateway/Watchdog 관련
- [ ] `openclaw doctor --fix` 실행
- [ ] `openclaw daemon install --force` (토큰 불일치 시)
- [ ] launchd-guardian.sh 재시작 확인
- [ ] Grace Period 30초 대기 후 재확인

## 5단계: 사후 처리

```bash
# 복구 확인
openclaw status
# Discord 알림 전송
~/.openclaw/scripts/alert.sh "crisis-resolved" "서비스 복구 완료: [원인] / [해결책]"
```

**사후 문서화**: CLAUDE.md 주요 변경사항 섹션 업데이트

## 참고
- 자가복구 문서: `~/openclaw/docs/self-healing-system.md`
- 응급 복구: `~/openclaw/scripts/emergency-recovery.sh`
- 알림 스크립트: `~/.openclaw/scripts/alert.sh`
