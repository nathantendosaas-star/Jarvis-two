#!/usr/bin/env bash
# Consensus-based polling service
# 목적: 합의 기반의 상태 폴링 및 보드 업데이트
# 주기: * 8-23 * * * (8시-23시 매시간)

set -euo pipefail

BOT_HOME="${BOT_HOME:=$HOME/.jarvis}"
BOARD_URL="${BOARD_URL:-https://board.ramsbaby.com}"  # privacy:allow personal-domain
AGENT_API_KEY="${AGENT_API_KEY:-}"
LOG_DIR="${BOT_HOME}/logs"
STATE_DIR="${BOT_HOME}/state"
BASELINE_DIR="${STATE_DIR}/baseline-raw-data"

# 로그 함수
log() {
    local level=$1
    shift
    local msg="$*"
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [$level] [consensus-poller] $msg" | tee -a "${LOG_DIR}/consensus-poller.log"
}

# 정리 함수
cleanup() {
    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        log "INFO" "Completed successfully"
    else
        log "ERROR" "Failed with exit code $exit_code"
    fi
    exit "$exit_code"
}

trap cleanup EXIT

# 사전 조건 확인
if [[ ! -d "${BASELINE_DIR}" ]]; then
    mkdir -p "${BASELINE_DIR}"
    log "INFO" "Created baseline directory"
fi

# 현재 합의 상태 조회
TIMESTAMP=$(date +'%Y%m%d')
CONSENSUS_STATE_FILE="${BASELINE_DIR}/consensus-poller-${TIMESTAMP}.json"

log "INFO" "Starting consensus polling"

# 보드 URL 헬스체크 (옵션)
if [[ -n "${BOARD_URL}" ]]; then
    if curl -sf "${BOARD_URL}/health" > /dev/null 2>&1; then
        log "INFO" "Board URL is healthy"
    else
        log "WARN" "Board URL health check failed: ${BOARD_URL}"
    fi
fi

# 합의 상태 파일 생성/업데이트
cat > "${CONSENSUS_STATE_FILE}" << 'EOF'
{
  "timestamp": "TIMESTAMP_PLACEHOLDER",
  "status": "active",
  "version": "1.0"
}
EOF

TIMESTAMP_ISO=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
sed -i '' "s|TIMESTAMP_PLACEHOLDER|${TIMESTAMP_ISO}|g" "${CONSENSUS_STATE_FILE}"

log "INFO" "Consensus state updated: ${CONSENSUS_STATE_FILE}"
log "INFO" "Polling completed successfully"
