#!/usr/bin/env bash
# PreToolUse hook: blocks dangerous bash commands
# Claude Code calls this with JSON on stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
CMD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

if [[ "$TOOL" != "Bash" ]]; then exit 0; fi

# Block rm -rf on root or home
if echo "$CMD" | grep -qE 'rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r' && echo "$CMD" | grep -qE '(/\s*$|/\s*"|~\s*$|\$HOME\s*$)'; then
    echo "BLOCKED: rm -rf on root/home directory detected. Use specific paths." >&2
    exit 2
fi

# Block force push to main/master
if echo "$CMD" | grep -qE 'git\s+push.*--force.*origin\s+(main|master)|git\s+push\s+-f.*origin\s+(main|master)'; then
    echo "BLOCKED: force push to main/master. Explicitly confirm this action first." >&2
    exit 2
fi

# Block DROP TABLE / TRUNCATE only when executed via SQL client
if echo "$CMD" | grep -qiE '(mysql|psql|sqlite3|sqlcmd)\b.*DROP\s+TABLE|(mysql|psql|sqlite3|sqlcmd)\b.*TRUNCATE\s+TABLE'; then
    echo "BLOCKED: DROP TABLE/TRUNCATE via SQL client detected. Explicitly confirm this destructive SQL action first." >&2
    exit 2
fi

# Block destructive GitHub repo actions without owner consent
# (visibility toggle, delete, archive — owner sovereignty per Iron Law 3)
# 2026-04-21: jarvis repo was silently switched to private, losing stars/forks.
# Bypass requires owner's explicit approval token in env: JARVIS_GH_DESTRUCTIVE_OK=1
if [[ "${JARVIS_GH_DESTRUCTIVE_OK:-0}" != "1" ]]; then
    if echo "$CMD" | grep -qiE 'gh\s+repo\s+edit\b.*--visibility\s*=?\s*private|gh\s+repo\s+edit\b.*--visibility\s*=?\s*internal'; then
        echo "BLOCKED: gh repo visibility → private/internal. Owner consent required." >&2
        echo "  Bypass (owner-only): JARVIS_GH_DESTRUCTIVE_OK=1 <cmd>" >&2
        exit 2
    fi
    if echo "$CMD" | grep -qiE 'gh\s+repo\s+(delete|archive)\b'; then
        echo "BLOCKED: gh repo delete/archive. Owner consent required (irreversible)." >&2
        echo "  Bypass (owner-only): JARVIS_GH_DESTRUCTIVE_OK=1 <cmd>" >&2
        exit 2
    fi
    if echo "$CMD" | grep -qiE 'gh\s+api\b.*(-X\s*DELETE|--method\s*DELETE).*repos/'; then
        echo "BLOCKED: gh api DELETE on repos/. Owner consent required." >&2
        echo "  Bypass (owner-only): JARVIS_GH_DESTRUCTIVE_OK=1 <cmd>" >&2
        exit 2
    fi
    if echo "$CMD" | grep -qiE 'gh\s+api\b.*repos/.*--field\s+private=true|gh\s+api\b.*repos/.*-f\s+private=true'; then
        echo "BLOCKED: gh api set private=true on repos/. Owner consent required." >&2
        echo "  Bypass (owner-only): JARVIS_GH_DESTRUCTIVE_OK=1 <cmd>" >&2
        exit 2
    fi
fi

exit 0
