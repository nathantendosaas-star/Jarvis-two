"""
Tool implementations the agent can call: file I/O, search, and shell
commands. Shell commands go through a safety layer -- readonly commands
run immediately, anything else asks for confirmation, and a fixed set of
destructive patterns always require confirmation even in auto-approve mode.
"""

import os
import re
import subprocess

import config

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdel\s+/f\s+/s\s+/q\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bshutdown\b",
    r"\bmkfs\b",
    r":\(\)\s*\{.*\};\s*:",  # fork bomb
    r"\bdd\s+if=",
    r">\s*/dev/sd",
    r"\bdiskpart\b",
    r"\breg\s+delete\b",
    r"\bgit\s+push\s+.*--force",
]

SAFE_READONLY_PREFIXES = [
    "dir", "ls", "cat", "type", "git status", "git log", "git diff",
    "git branch", "npm list", "npm --version", "pip list", "pip show",
    "python --version", "python3 --version", "node --version", "echo",
    "pwd", "cd", "whoami", "where ", "which ", "tree", "find ",
]


def is_dangerous(command: str) -> bool:
    cmd = command.lower()
    return any(re.search(pat, cmd) for pat in DANGEROUS_PATTERNS)


def is_safe_readonly(command: str) -> bool:
    cmd = command.strip().lower()
    return any(cmd.startswith(p) for p in SAFE_READONLY_PREFIXES)


def read_file(path):
    try:
        with open(path, "r", encoding="utf8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR reading {path}: {e}"


def write_file(path, content):
    try:
        dirpath = os.path.dirname(path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(path, "w", encoding="utf8") as f:
            f.write(content)
        return f"File written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"ERROR writing {path}: {e}"


def list_dir(path="."):
    try:
        entries = sorted(os.listdir(path))
        return "\n".join(entries) if entries else "(empty directory)"
    except Exception as e:
        return f"ERROR listing {path}: {e}"


def search_files(pattern, path=".", max_results=50):
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR invalid regex: {e}"

    matches = []
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append(f"{fpath}:{i}: {line.strip()}")
                            if len(matches) >= max_results:
                                return "\n".join(matches)
            except Exception:
                continue
    return "\n".join(matches) if matches else "No matches found."


def run_command(cmd, confirm_fn=None):
    """
    confirm_fn: callable(cmd) -> bool. If provided, gates any command that
    isn't obviously read-only. Dangerous commands should be checked by the
    caller before calling this (kept separate so callers can warn loudly).
    """
    if confirm_fn and not is_safe_readonly(cmd):
        if not confirm_fn(cmd):
            return "Command not executed: declined."

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=config.COMMAND_TIMEOUT_SECONDS,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        if not output:
            output = f"(finished, exit code {result.returncode}, no output)"
        return output
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {config.COMMAND_TIMEOUT_SECONDS}s."
    except Exception as e:
        return f"ERROR running command: {e}"
