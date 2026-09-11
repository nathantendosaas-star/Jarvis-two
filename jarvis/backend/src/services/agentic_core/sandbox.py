import os
import re
import sys
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BLOCKED_PATTERNS = [
    r"rmdir\s+/s", r"del\s+/f", r"\bformat\b",             # Windows destructive
    r"rm\s+-rf\s+/(?!\S)", r"rm\s+-rf\s+~",                 # Unix destructive
    r":\(\)\s*\{\s*:\|:&\s*\};:",                           # fork bomb
    r"mkfs", r"dd\s+if=.*of=/dev/", r">\s*/dev/sd[a-z]",
    r"\bshutdown\b", r"\breboot\b",
    r"curl.*\|\s*sh", r"wget.*\|\s*sh",                     # remote-script-to-shell piping
]

# Sensitive env prefixes/substrings to scrub
SCRUB_ENV_PATTERNS = [
    r"^AWS_", r"TOKEN$", r"KEY$", r"SECRET", r"PASSWORD", r"PRIVATE", r"AUTH"
]

def check_command_safety(cmd: str, cwd: Path) -> Tuple[bool, str]:
    """Checks command for blocked destructive patterns and path traversal escapes."""
    # 1. Destructive patterns
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return False, f"Blocked pattern '{pat}' detected."

    # 2. Path traversal check (prevent escaping the workspace via relative paths)
    # Search for traversal sequences in arguments
    traversal_match = re.search(r"\.\.(/|\\)", cmd)
    if traversal_match:
        # A simple check: if '..' is present, let's verify if the command mentions paths escaping cwd.
        # But to be safe, any command containing relative path traversals '..' should be rejected unless it can be resolved.
        # Let's enforce strict safety: refuse commands with ".." path traversal outside the workspace path.
        return False, "Relative path traversal '..' is forbidden in commands."

    return True, ""

def get_scrubbed_environment() -> Dict[str, str]:
    """Returns a copy of the current environment with all sensitive credentials scrubbed."""
    clean_env = {}
    for k, v in os.environ.items():
        # Check against scrub patterns
        should_scrub = False
        for pat in SCRUB_ENV_PATTERNS:
            if re.search(pat, k, re.IGNORECASE):
                should_scrub = True
                break

        if not should_scrub:
            clean_env[k] = v
    return clean_env

async def is_bubblewrap_available() -> bool:
    """Checks if bwrap (bubblewrap) executable is available in the system path."""
    bwrap_path = shutil.which("bwrap")
    if not bwrap_path:
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            "bwrap", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False

async def execute_sandboxed_command(
    cmd: str,
    cwd: Path,
    sandbox_enabled: bool = True,
    network_access: bool = True,
    timeout: int = 120
) -> Dict[str, Any]:
    """Executes a command inside our tiered sandbox environment.

    Level 1: Process-level env scrubbing + cwd lockdown + path traversal checking.
    Level 2: Kernel-level isolation using bubblewrap if bubblewrap is available and sandbox is enabled.
    """
    # 1. Verify safety first
    is_safe, err_msg = check_command_safety(cmd, cwd)
    if not is_safe:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Security Violation: {err_msg}"
        }

    # 2. Prepare scrubbed environment
    env = get_scrubbed_environment()
    if not network_access:
        # Set proxies to blackhole/invalid locations to sever network access in process level
        env["http_proxy"] = "http://127.0.0.1:99999"
        env["https_proxy"] = "http://127.0.0.1:99999"
        env["HTTP_PROXY"] = "http://127.0.0.1:99999"
        env["HTTPS_PROXY"] = "http://127.0.0.1:99999"

    # Ensure cwd is resolved absolute
    cwd_resolved = cwd.resolve()

    # 3. Choose Level (Bubblewrap vs Subprocess)
    bwrap_ok = False
    if sandbox_enabled:
        bwrap_ok = await is_bubblewrap_available()

    if sandbox_enabled and bwrap_ok:
        # Build bubblewrap command
        # --ro-bind / / binds root as read-only. We want to bind the specific cwd writeable
        # --bind cwd cwd allows write operations inside workspace
        bwrap_args = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--bind", str(cwd_resolved), str(cwd_resolved),
            "--chdir", str(cwd_resolved),
        ]
        if not network_access:
            bwrap_args.append("--unshare-net")

        # Append target shell command
        bwrap_args.extend(["sh", "-c", cmd])

        try:
            proc = await asyncio.create_subprocess_exec(
                *bwrap_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(cwd_resolved)
            )
        except Exception as e:
            # Fallback to standard process execution if bubblewrap spawning fails
            bwrap_ok = False

    if not sandbox_enabled or not bwrap_ok:
        # Process Level 1 execution
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(cwd_resolved)
            )
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Failed to spawn process: {e}"
            }

    # Await output with timeout guard
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=float(timeout)
        )
        exit_code = proc.returncode
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": stderr_bytes.decode("utf-8", errors="replace")
        }
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.communicate()
        except ProcessLookupError:
            pass
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds and was terminated."
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution error: {e}"
        }
