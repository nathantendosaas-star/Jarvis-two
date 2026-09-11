---
paths:
  - "**/*.sh"
  - "**/*.bash"
---

# Shell 스크립팅 규칙

## 필수 헤더

모든 shell 스크립트는 반드시 아래 2줄로 시작.

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- `set -e`: 명령 실패 시 즉시 종료
- `set -u`: 미정의 변수 참조 시 오류
- `set -o pipefail`: 파이프 중간 실패도 감지

## 변수 처리

```bash
# 올바른 예
echo "$var"
cp "$src" "$dst"
for item in "${arr[@]}"; do echo "$item"; done

# 금지
echo $var          # 쿼팅 없음 → 단어 분리/glob 위험
for item in ${arr[@]}  # 배열도 반드시 쿼팅
```

- 모든 변수는 `"$var"` 형태로 쿼팅
- 배열은 `"${arr[@]}"` 형태
- 경로 변수는 특히 주의 (공백 포함 가능)

## 임시 파일 처리

```bash
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

# 작업...
echo "data" > "$tmp"
```

- `mktemp`로 고유 임시 파일 생성
- `trap ... EXIT`으로 스크립트 종료 시 반드시 정리
- 임시 디렉토리: `tmp=$(mktemp -d)` + `trap 'rm -rf "$tmp"' EXIT`

## 에러 처리

```bash
# 명시적 exit code
command || { echo "[ERROR] command 실패" >&2; exit 1; }

# 조건부 실패 허용 (남용 금지)
command || true   # 정말 무시해도 되는 경우만

# 실패 원인 로깅 후 종료
if ! command; then
    log "command 실패 (exit $?)"
    exit 1
fi
```

- 실패 시 exit code 명시 (`exit 1` 등)
- `|| true` 남용 금지 — 실패를 조용히 삼키면 디버깅 불가
- stderr(`>&2`)에 에러 메시지 출력

## 로그 패턴

```bash
log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "시작"
log "처리 완료: $count 건"
```

- 타임스탬프 포함 로그로 실행 시간 추적 가능
- 중요 단계마다 로그 남기기

## 크론 Safe Wrapper

반복 실행 스크립트는 아래 패턴 적용 권장.

```bash
#!/usr/bin/env bash
set -euo pipefail

LOCK="/tmp/$(basename "$0").lock"
LOG="$HOME/.jarvis/logs/$(basename "$0" .sh).log"

# mutex lock (중복 실행 방지)
exec 9>"$LOCK"
flock -n 9 || { echo "이미 실행 중" >&2; exit 0; }

# nice +10 (CPU 우선순위 낮춤)
renice -n 10 $$ >/dev/null 2>&1 || true

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

# timeout 감싸기 (무한 대기 방지)
timeout 300 bash -c '
    # 실제 작업
    log "작업 시작"
' || log "[WARN] timeout 또는 실패"
```

## Brave Search API 정책

월 2,000만 회 한도 / Rate Limit 초당 20개

```bash
# 올바른 예: 2-3개씩 병렬 묶기
search_brave "query1" &
search_brave "query2" &
wait

# 금지: 4개 이상 동시 호출
search_brave "q1" & search_brave "q2" & search_brave "q3" & search_brave "q4" &  # 위험
```

- 병렬 검색은 **2-3개씩** 묶어서 호출
- 4개 이상 동시 실행 시 Rate Limit 위험
- `site:` 연산자 + 구체적 키워드로 호출 횟수 최소화
- 중요 검색 먼저 → 추가 검색 순서로 진행

## Jarvis 명명 규칙

스크립트/함수: `[도메인]-[대상]-[동작/상태]` 패턴

- 도메인: `discord`, `jarvis`, `watchdog`, `rag`, `alert`
- 예: `bot-watchdog.sh`, `rag-index.mjs`, `jarvis-cron.sh`
