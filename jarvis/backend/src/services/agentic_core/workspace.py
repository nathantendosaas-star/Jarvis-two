import os
import shutil
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, Literal

class WorkspaceHandle:
    def __init__(
        self,
        path: Path,
        mode: Literal["inherit", "share", "branch"],
        isolated: bool,
        branch_name: Optional[str] = None
    ):
        self.path = path
        self.mode = mode
        self.isolated = isolated
        self.branch_name = branch_name

class WorkspaceManager:
    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path.cwd().resolve()

    async def _run_git(self, args: list, cwd: Path) -> tuple[bool, str]:
        """Helper to run a git command asynchronously."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd)
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return True, stdout.decode("utf-8", errors="replace").strip()
            else:
                return False, stderr.decode("utf-8", errors="replace").strip()
        except Exception as e:
            return False, str(e)

    async def provision(self, parent_workspace: WorkspaceHandle, mode: str, child_id: str) -> WorkspaceHandle:
        """Provisions a new WorkspaceHandle based on mode: inherit, share, or branch."""
        if mode == "inherit":
            return parent_workspace

        if mode == "share":
            return WorkspaceHandle(
                path=parent_workspace.path,
                mode="share",
                isolated=False
            )

        if mode == "branch":
            # Create a unique temporary directory name
            tmp_parent = Path(tempfile.gettempdir()) / "agent-worktrees"
            tmp_parent.mkdir(parents=True, exist_ok=True)
            tmp_dir = tmp_parent / f"agent-wt-{child_id[:8]}"

            # Make sure it's deleted if somehow it exists
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

            branch_name = f"agent/{child_id[:8]}"

            # Run git worktree add
            ok, err = await self._run_git(
                ["worktree", "add", str(tmp_dir), "-b", branch_name],
                cwd=parent_workspace.path
            )
            if not ok:
                # Fall back to 'share' if worktree cannot be created (e.g. not a git repo, or dirty branch)
                print(f"Git worktree creation failed: {err}. Falling back to 'share' workspace mode.")
                return WorkspaceHandle(
                    path=parent_workspace.path,
                    mode="share",
                    isolated=False
                )

            return WorkspaceHandle(
                path=tmp_dir,
                mode="branch",
                isolated=True,
                branch_name=branch_name
            )

        # Default fallback
        return parent_workspace

    async def cleanup(self, ws: WorkspaceHandle):
        """Cleans up isolated workspaces by removing git worktrees and temporary branches."""
        if ws.isolated and ws.branch_name and ws.path.exists():
            # 1. Remove the git worktree
            ok, err = await self._run_git(
                ["worktree", "remove", "--force", str(ws.path)],
                cwd=self.repo_root
            )
            if not ok:
                print(f"Error removing git worktree {ws.path}: {err}")
                # Try physical deletion if worktree fails
                shutil.rmtree(ws.path, ignore_errors=True)

            # 2. Delete the temporary branch
            ok_b, err_b = await self._run_git(
                ["branch", "-D", ws.branch_name],
                cwd=self.repo_root
            )
            if not ok_b:
                print(f"Error deleting git branch {ws.branch_name}: {err_b}")
