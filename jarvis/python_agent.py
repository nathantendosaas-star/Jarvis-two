import json
import os
import subprocess
import requests
import re
import ssl
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; env vars must be set manually

# ==============================
# OpenRouter Configuration
# ==============================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Supported models:
# - "deepseek/deepseek-v4-flash" (default — fast, capable)
# - "deepseek/deepseek-r1" (reasoning model)
# - "google/gemma-2-27b-it" / "google/gemma-2-9b-it"
MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

URL = "https://openrouter.ai/api/v1/chat/completions"

# ── SSL fix for Python 3.14 (SSLEOFError / UNEXPECTED_EOF_WHILE_READING) ──
# Python 3.14 tightened TLS behaviour; some hosts (incl. OpenRouter) drop the
# connection before sending a close_notify alert. Mounting a custom adapter
# that does NOT require a clean shutdown resolves this without disabling cert
# verification entirely.
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class _TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)

_SESSION = requests.Session()
_SESSION.mount("https://", _TLSAdapter())
_SESSION.headers.update({
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:3000",
    "X-Title": "JARVIS AI OS",
})


WORKSPACE_ROOT = Path(__file__).resolve().parent

BLOCKED_COMMAND_PATTERNS = [
    r"rmdir\s+/s", r"del\s+/f", r"\bformat\b",             # Windows destructive
    r"rm\s+-rf\s+/(?!\S)", r"rm\s+-rf\s+~",                 # Unix destructive
    r":\(\)\s*\{\s*:\|:&\s*\};:",                           # fork bomb
    r"mkfs", r"dd\s+if=.*of=/dev/", r">\s*/dev/sd[a-z]",
    r"\bshutdown\b", r"\breboot\b",
    r"curl.*\|\s*sh", r"wget.*\|\s*sh",                     # remote-script-to-shell piping
]

SYSTEM_PROMPT = """
You are an autonomous terminal coding assistant powered by OpenRouter (Deepseek v4 Flash / Gemma).

You have these tools available. Always reply ONLY with valid JSON if you want to call a tool:

1. read_file
{
  "tool": "read_file",
  "path": "path/to/file.py"
}

2. write_file
{
  "tool": "write_file",
  "path": "path/to/file.py",
  "content": "file content here"
}

3. grep_search
{
  "tool": "grep_search",
  "pattern": "regex_pattern_here"
}

4. run_command (or execute_command)
{
  "tool": "run_command",
  "command": "python main.py"
}

5. web_fetch
{
  "tool": "web_fetch",
  "url": "https://example.com"
}

When you have the final answer, reply normally in plain text (not in tool JSON format) explaining what was done.
"""

conversation = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]

summary = ""

MAX_MESSAGES = 18


def chat(messages):
    if not OPENROUTER_API_KEY:
        print("[WARNING] OPENROUTER_API_KEY is not set. Please set it in your environment.")

    # reasoning is only supported on deepseek-r1, NOT on deepseek-v4-flash
    payload: dict = {
        "model": MODEL,
        "messages": messages,
    }
    if "deepseek-r1" in MODEL:
        payload["reasoning"] = {"enabled": True}

    r = _SESSION.post(
        URL,
        json=payload,
        timeout=300
    )

    r.raise_for_status()

    return r.json()["choices"][0]["message"]


def summarize():
    global conversation
    global summary

    msgs = [
        {
            "role": "system",
            "content":
            "Summarize the conversation for future memory. Keep important facts, file names, decisions, plans, variables and objectives."
        }
    ]

    msgs.extend(conversation[1:])

    result = chat(msgs)

    summary = result["content"]

    conversation = [
        conversation[0],
        {
            "role": "system",
            "content":
            "Conversation memory:\n" + summary
        }
    ]


def read_file(path):
    try:
        target = (WORKSPACE_ROOT / path).resolve()
        if not target.exists():
            return f"Error: {path} does not exist."
        return target.read_text(encoding="utf8")
    except Exception as e:
        return str(e)


def write_file(path, content):
    try:
        target = (WORKSPACE_ROOT / path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf8")
        return "File written."
    except Exception as e:
        return str(e)


def run_command(cmd):
    for pat in BLOCKED_COMMAND_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return f"Error: Command '{cmd}' blocked for security reasons."
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT)
        )

        return result.stdout + result.stderr

    except Exception as e:
        return str(e)


def grep_search(pattern):
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except Exception as e:
        return f"Error: Invalid regex: {e}"

    ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", ".storage"}
    matches = []

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for name in files:
            file_path = Path(root) / name
            try:
                # Limit size for safety
                if file_path.stat().st_size > 500_000:
                    continue
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(WORKSPACE_ROOT)
                            matches.append(f"{rel_path}:{i}: {line.strip()[:150]}")
                            if len(matches) >= 100:
                                break
            except Exception:
                continue
            if len(matches) >= 100:
                break
        if len(matches) >= 100:
            break

    return "\n".join(matches) if matches else "No matches found."


def web_fetch(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()

        # Simple extraction of title and body text to fit context gracefully
        text = r.text
        if "</html>" in text.lower():
            # Basic cleanup of script and style tags if HTML
            text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

        return text[:10000]
    except Exception as e:
        return f"Error fetching {url}: {e}"


def execute_tool(message):
    try:
        content = message["content"].strip()
        # Find JSON block
        if "{" in content and "}" in content:
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            json_str = content[start_idx:end_idx]
            tool = json.loads(json_str)
        else:
            return None
    except Exception:
        return None

    tool_name = tool.get("tool")
    if tool_name == "read_file":
        return read_file(tool.get("path"))

    if tool_name == "write_file":
        return write_file(tool.get("path"), tool.get("content", ""))

    if tool_name in ("run_command", "execute_command"):
        return run_command(tool.get("command") or tool.get("cmd"))

    if tool_name == "grep_search":
        return grep_search(tool.get("pattern"))

    if tool_name == "web_fetch":
        return web_fetch(tool.get("url"))

    return None


print("=" * 60)
print(f"JARVIS OpenRouter Agent ({MODEL})")
print("Type exit to quit.")
print("=" * 60)

while True:
    try:
        user = input("\nYou > ")
    except KeyboardInterrupt:
        break

    if user.lower() in ("exit", "quit"):
        break

    conversation.append(
        {
            "role": "user",
            "content": user
        }
    )

    while True:
        try:
            response = chat(conversation)
        except Exception as e:
            print(f"\n[OpenRouter Error] {e}")
            break

        conversation.append(
            {
                "role": "assistant",
                "content": response["content"]
            }
        )

        tool_result = execute_tool(response)

        if tool_result is None:
            print(f"\n{MODEL}:\n")
            print(response["content"])
            break

        print(f"\n[Tool Executed: {json.loads(response['content'].strip()[response['content'].find('{'):response['content'].rfind('}')+1]).get('tool')}]\n")
        print(tool_result[:1000] + ("\n...[Truncated]" if len(tool_result) > 1000 else ""))

        conversation.append(
            {
                "role": "user",
                "content": f"Tool result:\n{tool_result}"
            }
        )

    if len(conversation) > MAX_MESSAGES:
        summarize()
