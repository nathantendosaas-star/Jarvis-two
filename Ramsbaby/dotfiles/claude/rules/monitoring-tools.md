---
paths:
  - "**/*watchdog*"
  - "**/*monitor*"
  - "**/*health*"
  - "**/*doctor*"
  - "**/*alert*"
---

# 모니터링 도구 규칙

## 모니터링 정책

### Discord Bot 감시

- **침묵 15분** → `bot-watchdog.sh` 자동 재시작 트리거
- 로그 freshness 기준: `~/.jarvis/logs/discord-bot.log` 마지막 갱신 시각
- watchdog 자체 감시: `launchd-guardian.sh` (cron `*/3`)가 watchdog LaunchAgent 언로드 감지 → 자동 재등록

```bash
# watchdog 수동 상태 확인
launchctl list | grep jarvis
tail -20 ~/.jarvis/logs/bot-watchdog.log
```

### LaunchAgent 설정 원칙

| 설정 | 값 | 용도 |
|------|----|------|
| `KeepAlive` | `true` | OS 레벨 자동 재시작 (KeepAlive 데몬 전용) |
| `StartInterval` | `180` | watchdog 주기 (초) |

> **경고**: `StartCalendarInterval` / `StartInterval` LaunchAgent 신규 생성 금지. 신규 스케줄 태스크는 반드시 **crontab에만** 등록.

### 일일 건강 체크

```bash
# 매일 2회 자동 실행 (cron 1,31 * *)
~/.jarvis/scripts/system-health.sh

# 수동 점검
/doctor   # Claude Code 슬래시 명령어
```

---

## TUI 모니터링 도구

### macmon — Apple Silicon 전용

Apple Silicon(M 시리즈) CPU/GPU/전력/온도 실시간 모니터링.

```bash
macmon          # 기본 실행
macmon --help   # 옵션 확인
```

표시 항목: CPU 사용률, GPU 사용률, 전력 소비(W), 칩 온도(°C), 메모리 압력

### btop — 프로세스 모니터

```bash
btop            # 전체 프로세스, CPU, 메모리, 네트워크 현황
```

### wtfutil — 커스텀 위젯 대시보드

```bash
wtfutil         # 설정 기반 커스텀 위젯 대시보드 실행
```

---

## tmux 세션 관리

SSH 연결이 끊겨도 세션이 살아있어 장시간 작업 가능.

### 접속 방법

```bash
tmux attach -t claude1    # claude1 세션 접속
tmux attach -t claude2    # claude2 세션 접속
tc claude1                # 새 세션 생성 (tc = tmux new-session -s)
```

### 세션 목록

| 세션명 | 용도 |
|--------|------|
| `claude1` | Claude Code 인터랙티브 세션 #1 |
| `claude2` | Claude Code 인터랙티브 세션 #2 |

### tmux 기본 단축키

```
Ctrl+b d    — 세션에서 분리 (detach, 세션은 유지)
Ctrl+b [    — 스크롤 모드 (q로 종료)
Ctrl+b c    — 새 창 생성
Ctrl+b n/p  — 다음/이전 창
```

---

## ntfy 푸시 알림

### 설정 정보

| 항목 | 값 |
|------|-----|
| 서버 | `ntfy.sh` |
| 토픽 | `openclaw-f101e56cb98a` |
| 구독 기기 | Galaxy ntfy 앱 |

### 알림 전송

`alert.sh`는 Discord + ntfy 이중 전송으로 알림 누락 방지.

```bash
# 직접 전송
~/.jarvis/scripts/alert.sh "알림 제목" "내용"

# ntfy 단독 전송
curl -d "메시지 내용" ntfy.sh/openclaw-f101e56cb98a
```

> **참고**: ntfy는 Galaxy 포함 모든 기기 동기화. Apple Reminders(remindctl)는 Apple 전용이라 Galaxy 비호환.

---

## SSH 보안

### 설정 원칙

- **키 인증만** 허용 (패스워드 인증 차단)
- **root 직접 로그인** 차단

### 설정 파일

```
/etc/ssh/sshd_config.d/200-hardening.conf
```

```bash
# 설정 확인
sudo cat /etc/ssh/sshd_config.d/200-hardening.conf

# sshd 재시작 (설정 변경 후)
sudo launchctl kickstart -k system/com.openssh.sshd
```

> **경고**: sshd_config 수정 후 반드시 다른 터미널에서 접속 테스트 후 기존 세션 닫을 것. 잘못된 설정으로 SSH 잠김 위험.

---

## pmset 에너지 설정

Mac Mini 서버 무중단 운영을 위한 설정.

| 설정 | 값 | 의미 |
|------|----|------|
| `SleepDisabled` | `1` | 시스템 절전 비활성화 |
| `autorestart` | `1` | 정전/커널패닉 후 자동 재시작 |
| `displaysleep` | `0` | 디스플레이 절전 비활성화 |
| `disksleep` | `0` | 디스크 절전 비활성화 |

```bash
# 현재 설정 확인
pmset -g

# 설정 변경 (예시)
sudo pmset -a SleepDisabled 1
sudo pmset -a autorestart 1
sudo pmset -a displaysleep 0
sudo pmset -a disksleep 0
```
