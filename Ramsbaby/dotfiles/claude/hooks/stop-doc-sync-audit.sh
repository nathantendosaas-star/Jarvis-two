#!/usr/bin/env bash
# stop-doc-sync-audit.sh v2 — 코드-문서 정합성 감사 (doc-map.json 기반)
# Phase 1+2: 특정 파일명 경고 + pending-doc-updates.json 생성
# Stop hook (async, 15s timeout)

BOT_HOME="${HOME}/.jarvis"
SESSION_TS="${BOT_HOME}/state/.claude-session-start"
VIOLATION_LOG="${BOT_HOME}/logs/doc-sync-violations.log"
DOC_MAP="${BOT_HOME}/config/doc-map.json"
PENDING_UPDATES="${BOT_HOME}/state/pending-doc-updates.json"
WEBHOOK_URL="$(python3 -c "import json; d=json.load(open('${BOT_HOME}/config/monitoring.json')); print(d.get('webhooks',{}).get('jarvis-system',''))" 2>/dev/null)"

log() { echo "[$(date '+%F %T')] [doc-sync-audit] $1" >> "$VIOLATION_LOG"; }

if [[ ! -f "$SESSION_TS" ]]; then log "No session timestamp — skip"; exit 0; fi
if [[ ! -f "$DOC_MAP" ]]; then log "No doc-map.json — skip"; exit 0; fi

# 코드/설정 파일 변경 감지
code_changed=$(find \
    "$BOT_HOME/lib" "$BOT_HOME/bin" "$BOT_HOME/scripts" \
    "$BOT_HOME/discord" "$BOT_HOME/config" \
    "$HOME/.claude/hooks" \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/logs/*" \
    -not -path "*/cache/*" \
    -not -path "*/rag/lancedb/*" \
    \( -name "*.mjs" -o -name "*.js" -o -name "*.sh" -o -name "*.json" \) \
    -newer "$SESSION_TS" 2>/dev/null \
    | grep -v "session-changelog\|\.claude-session-start\|tasks.db\|health.json\|pending-doc-updates\|doc-map\|commitments" \
    | sort)

if [[ -z "$code_changed" ]]; then
    log "No code changes — skip"
    [[ -f "$PENDING_UPDATES" ]] && rm -f "$PENDING_UPDATES"
    exit 0
fi

code_count=$(echo "$code_changed" | wc -l | tr -d ' ')

# 문서 변경 감지
docs_changed=$(find \
    "$BOT_HOME/docs" "$BOT_HOME/context" "$BOT_HOME/adr" \
    -name "*.md" \
    -newer "$SESSION_TS" 2>/dev/null \
    | grep -v "session-changelog\|discord-history" \
    | sort)

docs_count=$(echo "$docs_changed" | grep -c . 2>/dev/null || echo 0)
now=$(date '+%Y-%m-%d %H:%M')

# Python 스크립트로 doc-map.json 기반 누락 문서 탐지
ANALYZE_PY="${BOT_HOME}/state/.doc-sync-analyze.py"
cat > "$ANALYZE_PY" << 'PYEOF'
import json, sys, os

doc_map_path, code_raw, docs_raw, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
doc_map = json.load(open(doc_map_path))
code_files = [f.strip() for f in code_raw.split("\n") if f.strip()]
docs_basenames = set(os.path.basename(f.strip()) for f in docs_raw.split("\n") if f.strip())
home = os.path.expanduser("~")

missing = {}
for f in code_files:
    fname = os.path.basename(f)
    frel = f.replace(home + "/", "")
    for pattern in doc_map.get("patterns", []):
        mg = pattern.get("match_glob", "")
        if mg and (mg in f or mg in fname or fname in mg):
            for doc in pattern.get("docs", []):
                if os.path.basename(doc) not in docs_basenames:
                    if doc not in missing:
                        missing[doc] = {"reason": pattern.get("reason", ""), "triggered_by": []}
                    if frel not in missing[doc]["triggered_by"]:
                        missing[doc]["triggered_by"].append(frel)

if mode == "json":
    print(json.dumps(missing, ensure_ascii=False))
elif mode == "count":
    print(len(missing))
elif mode == "pending":
    session_mtime = str(int(os.path.getmtime(sys.argv[5]) * 1000)) if len(sys.argv) > 5 else "0"
    output = {
        "generated_at": sys.argv[6] if len(sys.argv) > 6 else "",
        "session_ts": session_mtime,
        "code_files_changed": [f.replace(home + "/", "") for f in code_files],
        "updates_needed": [
            {"doc_path": doc, "full_path": home + "/.jarvis/" + doc,
             "reason": info["reason"], "triggered_by": info["triggered_by"], "status": "pending"}
            for doc, info in missing.items()
        ]
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
elif mode == "discord_missing":
    for doc, info in list(missing.items())[:5]:
        triggers = ", ".join(info["triggered_by"][:2])
        print(f"- `{doc}` ({triggers})")
PYEOF

missing_docs_json=$(python3 "$ANALYZE_PY" "$DOC_MAP" "$code_changed" "$docs_changed" "json" 2>/dev/null || echo "{}")
missing_count=$(python3 "$ANALYZE_PY" "$DOC_MAP" "$code_changed" "$docs_changed" "count" 2>/dev/null || echo 0)

# pending-doc-updates.json 생성
if [[ "$missing_count" -gt 0 ]]; then
    python3 "$ANALYZE_PY" "$DOC_MAP" "$code_changed" "$docs_changed" "pending" "$SESSION_TS" "$now" > "$PENDING_UPDATES"
    log "pending-doc-updates.json 생성: ${missing_count}개 문서 누락"
fi

rm -f "$ANALYZE_PY"

if [[ "$docs_count" -gt 0 && "$missing_count" -eq 0 ]]; then
    log "OK: code=${code_count} docs=${docs_count} — 정합성 유지됨"
    [[ -f "$PENDING_UPDATES" ]] && rm -f "$PENDING_UPDATES"
    exit 0
fi

if [[ "$missing_count" -eq 0 ]]; then
    log "OK: code=${code_count} — doc-map 매핑 없는 변경 (문서 불필요)"
    exit 0
fi

log "VIOLATION: code=${code_count} docs=${docs_count} missing=${missing_count}"

# Discord 경고
if [[ -n "$WEBHOOK_URL" ]]; then
    code_list=$(echo "$code_changed" | sed "s|${HOME}/||" | head -6 | tr '\n' '\n')
    DISCORD_PY="${BOT_HOME}/state/.doc-sync-discord.py"
    cat > "$DISCORD_PY" << PYEOF2
import json, sys
code_raw, missing_json_path, mc_str, dc_str, now_str = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
mc, dc = int(mc_str), int(dc_str)
missing = json.load(open(missing_json_path))
code_lines = [l.strip() for l in code_raw.strip().split("\n") if l.strip()][:6]
code_fmt = "\n".join(["- " + l for l in code_lines])
missing_fmt = "\n".join([f"- \`{doc}\` ({', '.join(info['triggered_by'][:2])})" for doc, info in list(missing.items())[:5]])
title = f"⚠️ 문서 동기화 미확인 — {mc}개 문서 누락" if dc == 0 else f"⚠️ 일부 문서 미업데이트 — {mc}개 누락"
msg = {"username": "Jarvis Doc Auditor", "embeds": [{"title": title, "description": f"**변경된 코드:**\n{code_fmt}\n\n**업데이트 필요한 문서:**\n{missing_fmt}\n\n오늘 23:00 doc-sync-auditor가 draft를 자동 생성합니다.", "color": 0xFEE75C, "footer": {"text": f"{now_str} · stop-doc-sync-audit.sh v2"}}]}
print(json.dumps(msg))
PYEOF2
    # missing JSON을 임시 파일로 저장
    MISSING_TMP="${BOT_HOME}/state/.doc-sync-missing-tmp.json"
    echo "$missing_docs_json" > "$MISSING_TMP"
    payload=$(python3 "$DISCORD_PY" "$code_list" "$MISSING_TMP" "$missing_count" "$docs_count" "$now" 2>/dev/null)
    rm -f "$DISCORD_PY" "$MISSING_TMP"
    if [[ -n "$payload" ]]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            -o /dev/null --max-time 8 2>/dev/null
        log "Discord warning sent: missing=${missing_count}"
    fi
fi

exit 0
