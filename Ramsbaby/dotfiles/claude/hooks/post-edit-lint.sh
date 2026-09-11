#!/bin/bash
# PostToolUse hook: Write|Edit 후 자동 린트/포맷 체크
# exit 2 = Claude Code에게 에러 피드백 (즉시 수정 트리거)
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0
[ -f "$FILE_PATH" ] || exit 0

EXT="${FILE_PATH##*.}"
ERRORS=""

case "$EXT" in
  sh)
    # set -e 스크립트에서 [[ ]] && cmd 패턴 즉시 경고
    if grep -qE '^[[:space:]]*set -[a-zA-Z]*e' "$FILE_PATH" 2>/dev/null; then
      bad_lines=$(grep -nE '\[\[.*\]\]\s*&&\s*[^|]' "$FILE_PATH" 2>/dev/null \
        | grep -v '^[0-9]*:[[:space:]]*#' \
        | grep -v '^[0-9]*:[[:space:]]*if ' \
        | grep -v '^[0-9]*:[[:space:]]*elif ' \
        | grep -v '||[[:space:]]*true' || true)
      if [ -n "$bad_lines" ]; then
        ERRORS="⚠️ set-e 안티패턴 ($FILE_PATH):\n$bad_lines\nFIX: [[ cond ]] && cmd → if [[ cond ]]; then cmd; fi"
      fi
    fi
    # claude -p 호출 시 timeout 필수 — bare 호출 차단
    bare_claude=$(grep -nE '[^a-z_]claude -p' "$FILE_PATH" 2>/dev/null \
      | grep -v '^\s*#' \
      | grep -v 'timeout.*claude -p' \
      | grep -v '_safe_claude' \
      | grep -v 'claude -p.*기반' \
      | grep -v '예:.*claude' \
      | grep -v '^[0-9]*:[[:space:]]*#' \
      | grep -v 'grep.*claude' \
      | grep -v 'cmd+=.*claude -p' \
      | grep -v 'log_warn.*claude' \
      | grep -v 'log_error.*claude' \
      | grep -v '".*claude -p.*"' || true)
    if [ -n "$bare_claude" ]; then
      ERRORS="${ERRORS}${ERRORS:+\n}❌ claude -p timeout 누락 ($FILE_PATH):\n$bare_claude\nFIX: timeout 180 claude -p ... 또는 _safe_claude 사용 (source lib/common.sh)"
    fi
    ;;

  json)
    # JSON 유효성 검사 — stdin으로 전달 (파일 경로 보간 인젝션 방지)
    result=$(node -e "
      try {
        JSON.parse(require('fs').readFileSync(0, 'utf8'));
        process.exit(0);
      } catch(e) {
        console.error('JSON 파싱 오류: ' + e.message);
        process.exit(1);
      }
    " < "$FILE_PATH" 2>&1)
    if [ $? -ne 0 ]; then
      ERRORS="❌ JSON 유효성 실패 ($FILE_PATH):\n$result\n이스케이프 안 된 쌍따옴표(\") 또는 문법 오류를 확인하세요."
    fi
    ;;

  js|mjs|cjs)
    # 1) Node.js 구문 검사
    result=$(node --check "$FILE_PATH" 2>&1)
    if [ $? -ne 0 ]; then
      ERRORS="❌ JS 구문 오류 ($FILE_PATH):\n$result"
    else
      # 2) ESLint (설치된 경우) — undefined 변수 등 런타임 오류 사전 차단
      ESLINT_BIN=""
      # 프로젝트 로컬 eslint 우선
      DIR="$FILE_PATH"
      while [ "$DIR" != "/" ]; do
        DIR=$(dirname "$DIR")
        if [ -f "$DIR/node_modules/.bin/eslint" ]; then
          ESLINT_BIN="$DIR/node_modules/.bin/eslint"
          break
        fi
      done
      [ -z "$ESLINT_BIN" ] && command -v eslint &>/dev/null && ESLINT_BIN="eslint"

      if [ -n "$ESLINT_BIN" ]; then
        # .mjs 또는 package.json "type":"module" 또는 파일 내 import 사용 시 module
        PARSER_OPTS='{"sourceType":"script"}'
        PKG_DIR=$(dirname "$FILE_PATH")
        PKG_TYPE=""
        [ -f "$PKG_DIR/package.json" ] && PKG_TYPE=$(node -e "try{const p=require('$PKG_DIR/package.json');process.stdout.write(p.type||'')}catch(e){}" 2>/dev/null)
        if [ "$EXT" = "mjs" ] || [ "$PKG_TYPE" = "module" ] || grep -qE '^import ' "$FILE_PATH" 2>/dev/null; then
          PARSER_OPTS='{"sourceType":"module"}'
        fi
        lint_result=$("$ESLINT_BIN" --no-eslintrc \
          --rule '{"no-undef": "error", "no-unused-vars": "warn"}' \
          --env es2022,node \
          --parser-options "$PARSER_OPTS" \
          "$FILE_PATH" 2>&1)
        lint_exit=$?
        if [ $lint_exit -ne 0 ]; then
          # error 레벨만 블로킹 (warn은 통과)
          if echo "$lint_result" | grep -q " error "; then
            ERRORS="❌ ESLint 오류 ($FILE_PATH):\n$lint_result\n수정 후 재시도하세요."
          fi
        fi
      fi
    fi
    ;;

  ts|tsx|jsx)
    # TypeScript: tsc --noEmit (tsconfig 있을 때만)
    TS_DIR=$(dirname "$FILE_PATH")
    if [ -f "$TS_DIR/tsconfig.json" ] || [ -f "$TS_DIR/../tsconfig.json" ]; then
      if command -v npx &>/dev/null; then
        result=$(npx --no tsc --noEmit 2>&1 | head -20)
        if [ $? -ne 0 ]; then
          ERRORS="⚠️ TypeScript 오류 ($FILE_PATH):\n$result"
        fi
      fi
    fi
    ;;

  py)
    if command -v ruff &>/dev/null; then
      result=$(ruff check "$FILE_PATH" 2>&1)
      if [ $? -ne 0 ]; then
        ERRORS="⚠️ Python lint ($FILE_PATH):\n$result"
      fi
    fi
    ;;

  plist)
    # LaunchAgent 스케줄 태스크 생성 차단 — KeepAlive 데몬만 허용
    if grep -qE 'StartCalendarInterval|StartInterval' "$FILE_PATH" 2>/dev/null; then
      if ! grep -q 'KeepAlive' "$FILE_PATH" 2>/dev/null; then
        ERRORS="❌ 스케줄 LaunchAgent 생성 금지 ($FILE_PATH)\n정책: 주기적 태스크는 crontab에 등록. LaunchAgent는 KeepAlive 데몬만 허용.\n참고: ~/CLAUDE.md 'LaunchAgent vs Crontab 원칙'"
      fi
    fi
    ;;
esac

if [ -n "$ERRORS" ]; then
  echo -e "$ERRORS"
  exit 2  # exit 2 = Claude Code에게 즉시 피드백
fi

# Discord 봇 파일 수정 시 재시작 안내
case "$FILE_PATH" in
  */.jarvis/discord/*|*/.jarvis/lib/*|*/.jarvis/bin/*)
    echo "ℹ️  Jarvis 봇 파일 수정됨 — 반영하려면: bash ~/.jarvis/scripts/deploy-with-smoke.sh"
    ;;
esac

exit 0
