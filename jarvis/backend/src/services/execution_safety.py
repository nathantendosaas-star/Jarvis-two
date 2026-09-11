"""Execution Safety Layer — Git pre-execution snapshots, instant rollback, pre-check completion gate, and patch-only diffs."""

import subprocess
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def create_git_snapshot(task_id: str) -> Dict[str, Any]:
    """Take a pre-execution git commit snapshot before file modifications."""
    try:
        subprocess.run(["git", "add", "."], cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        res = subprocess.run(
            ["git", "commit", "-m", f"snapshot: jarvis-agent task {task_id}"],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True
        )
        return {"success": True, "message": res.stdout.strip() or "Snapshot recorded"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def rollback_git_snapshot() -> Dict[str, Any]:
    """Instantly rollback workspace modifications to prior state."""
    try:
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        return {"success": True, "message": "Rollback completed successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def evaluate_completion_check(task_type: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Evaluates fast completion scripts prior to calling LLMs for queued tasks."""
    if task_type == "check_file_exists":
        file_path = WORKSPACE_ROOT / args.get("path", "")
        if file_path.exists():
            return {"completed": True, "result": f"File '{args.get('path')}' already exists."}
    return None


def generate_patch_diff(rel_path: str, new_content: str) -> Dict[str, Any]:
    """Save proposed landing page or script edits as a patch diff for review."""
    patches_dir = WORKSPACE_ROOT / "Cached" / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    patch_file = patches_dir / f"{Path(rel_path).name}.patch"

    diff_text = f"--- a/{rel_path}\n+++ b/{rel_path}\n@@ proposed change @@\n{new_content[:500]}..."
    patch_file.write_text(diff_text, encoding="utf-8")

    return {"success": True, "patch_path": str(patch_file.relative_to(WORKSPACE_ROOT)), "diff": diff_text}
