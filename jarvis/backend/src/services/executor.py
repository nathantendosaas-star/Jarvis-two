"""Executor service — launches Python scripts as async subprocesses and watches them.

Flow:
  1. launch_script()  → creates a Job record, spawns subprocess, schedules background
                        watcher, returns job_id immediately to the caller (AI tool).
  2. _watch_process() → background coroutine; collects stdout/stderr, waits for exit,
                        updates the Job record with final status using a fresh DB session.
  3. wait_for_job()   → called by the AI's await_job tool; polls the DB until the job
                        reaches a terminal state or a guard timeout fires.

Security:
  - Only .py files inside WORKSPACE_ROOT are allowed.
  - Subprocess env inherits the server env plus JARVIS_JOB_ID and JARVIS_CALLBACK_URL
    so the script can POST back to /api/jobs/{id}/complete when it finishes.
"""

import sys
import os
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_session
from ..models.job import Job
from ..services.file import WORKSPACE_ROOT

# How long (chars) to keep from the tail of stdout/stderr logs
_LOG_CAP = 4000

# Base URL for the callback endpoint — scripts POST here when done
_CALLBACK_BASE = "http://127.0.0.1:8000/api/jobs"


# ---------------------------------------------------------------------------
# Public: launch a script
# ---------------------------------------------------------------------------

async def launch_script(
    db: AsyncSession,
    script_rel_path: str,
    timeout: int = 300,
) -> str:
    """Create a Job record and start the script as a background subprocess.

    Returns the job_id immediately — does NOT wait for the script to finish.
    The script is passed JARVIS_JOB_ID and JARVIS_CALLBACK_URL as env vars
    so it can signal completion without needing them baked into the source.
    """
    # ── Validation ──────────────────────────────────────────────────────────
    if not script_rel_path.endswith(".py"):
        raise ValueError("Only .py scripts are allowed.")

    abs_path = (WORKSPACE_ROOT / script_rel_path.lstrip("/")).resolve()
    try:
        abs_path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError("Script path escapes workspace root — access denied.")

    if not abs_path.exists():
        raise FileNotFoundError(f"Script not found: {script_rel_path}")

    # ── Create Job record ────────────────────────────────────────────────────
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        script_path=script_rel_path,
        status="queued",
    )
    db.add(job)
    await db.flush()

    # ── Build subprocess env ─────────────────────────────────────────────────
    callback_url = f"{_CALLBACK_BASE}/{job_id}/complete"
    child_env = {
        **os.environ,
        "JARVIS_JOB_ID": job_id,
        "JARVIS_CALLBACK_URL": callback_url,
    }

    # ── Launch subprocess ────────────────────────────────────────────────────
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(abs_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=child_env,
    )

    # Update to running with PID
    job.status = "running"
    job.pid = process.pid
    job.started_at = datetime.now(timezone.utc)
    await db.flush()

    # ── Schedule background watcher ──────────────────────────────────────────
    asyncio.ensure_future(_watch_process(job_id, process, timeout))

    return job_id


# ---------------------------------------------------------------------------
# Public: wait for a job to finish (called by the AI's await_job tool)
# ---------------------------------------------------------------------------

async def wait_for_job(
    db: AsyncSession,
    job_id: str,
    poll_interval: float = 1.5,
    timeout: int = 310,
) -> dict:
    """Poll the database until the job reaches a terminal state.

    Returns a dict compatible with the AI tool response format:
      { success, job_id, status, output_path, error }
    """
    elapsed = 0.0
    while elapsed < timeout:
        job = await db.get(Job, job_id)
        if job is None:
            return {
                "success": False,
                "job_id": job_id,
                "status": "not_found",
                "output_path": None,
                "error": f"Job {job_id} not found in database.",
            }

        if job.status in ("done", "failed"):
            return {
                "success": job.status == "done",
                "job_id": job_id,
                "status": job.status,
                "output_path": job.output_path,
                "error": job.error_message,
            }

        # Expire cached state so next get() hits the DB
        await db.refresh(job)
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    # Guard timeout — the watcher will eventually kill the process too
    return {
        "success": False,
        "job_id": job_id,
        "status": "timeout",
        "output_path": None,
        "error": f"await_job timed out after {timeout}s waiting for job to complete.",
    }


# ---------------------------------------------------------------------------
# Internal: background process watcher
# ---------------------------------------------------------------------------

async def _watch_process(job_id: str, process: asyncio.subprocess.Process, timeout: int) -> None:
    """Collect stdout/stderr, enforce timeout, and write final status to the DB.

    Uses a fresh AsyncSession so it is independent of the request lifecycle.
    """
    stdout_data = b""
    stderr_data = b""
    error_message: Optional[str] = None

    try:
        stdout_data, stderr_data = await asyncio.wait_for(
            process.communicate(),
            timeout=float(timeout),
        )
    except asyncio.TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        error_message = f"Script timed out after {timeout}s and was terminated."
    except Exception as exc:
        error_message = f"Watcher error: {exc}"

    exit_code = process.returncode  # None if killed before exit

    # Decode and cap logs
    stdout_str = (stdout_data.decode("utf-8", errors="replace") if stdout_data else "")[-_LOG_CAP:]
    stderr_str = (stderr_data.decode("utf-8", errors="replace") if stderr_data else "")[-_LOG_CAP:]

    # Determine final status
    if error_message:
        final_status = "failed"
    elif exit_code == 0:
        final_status = "done"
    else:
        final_status = "failed"
        if not error_message and stderr_str:
            error_message = stderr_str[:500]

    # ── Persist result with a FRESH session ─────────────────────────────────
    async with async_session() as fresh_db:
        try:
            job = await fresh_db.get(Job, job_id)
            if job:
                # Only update if the callback hasn't already marked it done
                if job.status not in ("done",):
                    job.status = final_status
                    job.exit_code = exit_code
                    job.error_message = error_message
                job.stdout_log = stdout_str
                job.stderr_log = stderr_str
                job.finished_at = datetime.now(timezone.utc)
                await fresh_db.commit()
        except Exception:
            await fresh_db.rollback()
