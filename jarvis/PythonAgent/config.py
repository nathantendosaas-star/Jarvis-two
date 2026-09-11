"""
Configuration for the agent CLI.

All settings come from environment variables (or a local .env file, which
is NOT committed to git). Never put an API key directly in code -- that's
how keys end up leaked in screenshots, uploads, and repos.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads a .env file sitting next to this script, if present
except ImportError:
    pass  # python-dotenv not installed -- env vars set another way still work

API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("AGENT_MODEL", "deepseek/deepseek-v4-flash")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Safety / autonomy ---
# Read-only commands (dir, git status, etc.) run without asking.
# Anything else -- writes, installs, deletes, network calls -- asks first,
# unless you flip AUTO_APPROVE to true (then only genuinely dangerous
# patterns like `rm -rf`, `format`, `diskpart` still force a confirm).
AUTO_APPROVE = os.getenv("AGENT_AUTO_APPROVE", "false").lower() == "true"

# --- Agent limits ---
MAX_TOOL_ITERATIONS = int(os.getenv("AGENT_MAX_TOOL_ITERATIONS", "40"))
MAX_SUBAGENT_DEPTH = int(os.getenv("AGENT_MAX_SUBAGENT_DEPTH", "2"))
COMMAND_TIMEOUT_SECONDS = int(os.getenv("AGENT_COMMAND_TIMEOUT", "180"))

# --- Memory management ---
SUMMARIZE_AFTER_MESSAGES = int(os.getenv("AGENT_SUMMARIZE_AFTER", "24"))
KEEP_LAST_MESSAGES = int(os.getenv("AGENT_KEEP_LAST", "8"))


def check_setup():
    """Called once at startup. Warns loudly instead of failing silently."""
    if not API_KEY:
        print(
            "\n[WARN] OPENROUTER_API_KEY is not set.\n"
            "  Option 1 (persists across sessions) -- in cmd, run:\n"
            "      setx OPENROUTER_API_KEY \"your-key-here\"\n"
            "    then close and reopen cmd.\n"
            "  Option 2 (quick, this session only) -- in cmd, run:\n"
            "      set OPENROUTER_API_KEY=your-key-here\n"
            "  Option 3 -- create a .env file next to main.py containing:\n"
            "      OPENROUTER_API_KEY=your-key-here\n"
        )
        return False
    return True
