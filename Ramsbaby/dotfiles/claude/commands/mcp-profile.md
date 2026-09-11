---
description: "MCP 프로파일 전환. coding/research/jarvis/minimal 프로파일 교체. 'MCP 전환', '프로파일 바꿔', 'mcp-profile' 요청 시 사용."
---

# MCP 프로파일 전환

사용자가 지정한 프로파일로 `~/.mcp.json`을 실제로 교체합니다.

인자: $ARGUMENTS (openclaw / gostop / blog)

---

## 프로파일 정의

### openclaw
OpenClaw 인프라 작업 전용.
- **serena** (openclaw LSP): 스크립트 심볼 탐색
- **filesystem**: openclaw/clawd 소스 직접 접근
- **github**: PR/이슈 관리
- **sequential-thinking**: 디버깅 단계별 분석
- **moltbot-docs / clawdbot-docs**: 제품 문서

### gostop
고스톱 앱(Flutter/Dart) 개발 전용.
- **serena-gostop** (Flutter/Dart LSP): 위젯/클래스 심볼 탐색
- **context7**: Flutter/Dart 공식 문서 조회
- **github**: PR/이슈 관리
- **sequential-thinking**: 아키텍처 분석
- **brave-search**: 패키지/API 검색

### blog
블로그(Gatsby/React/TS) 작업 전용.
- **serena-blog** (Gatsby LSP): 컴포넌트/훅 심볼 탐색
- **context7**: React/Gatsby 공식 문서 조회
- **github**: PR/이슈 관리
- **sequential-thinking**: 빌드 분석
- **brave-search**: 라이브러리 검색

---

## 실행 방법

인자가 `openclaw`, `gostop`, `blog` 중 하나이면:
1. 아래 bash 명령어를 Bash 도구로 **즉시 실행**하세요:
   ```bash
   bash ~/.claude/scripts/mcp-switch.sh $ARGUMENTS
   ```
2. 실행 결과를 사용자에게 보여주세요.
3. "Claude Code를 재시작(새 세션 시작)해야 적용됩니다" 안내.

인자가 없거나 잘못된 경우: 3개 프로파일 요약 표시 후 선택 요청.

현재 프로파일 확인:
```bash
cat ~/.mcp-current-profile 2>/dev/null || echo "설정 없음 (기본값 사용 중)"
```
