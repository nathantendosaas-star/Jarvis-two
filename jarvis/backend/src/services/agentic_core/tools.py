import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Set
from .sandbox import execute_sandboxed_command
from .guards import StuckLoopDetected

class ToolResult:
    def __init__(self, content: str = "", error: Optional[str] = None):
        self.content = content
        self.error = error

    def to_json(self) -> str:
        if self.error:
            return json.dumps({"success": False, "error": self.error})
        return json.dumps({"success": True, "result": self.content})

class ToolRegistry:
    def __init__(self):
        self.native: Dict[str, Callable] = {}
        self.mcp_clients: Dict[str, Any] = {}
        self._register_natives()

    def register_native(self, name: str, func: Callable):
        self.native[name] = func

    def known_names(self) -> Set[str]:
        return set(self.native)

    def _register_natives(self):
        self.register_native("view_file", _tool_view_file)
        self.register_native("write_file", _tool_write_file)
        self.register_native("grep_search", _tool_grep_search)
        self.register_native("run_command", _tool_run_command)
        self.register_native("invoke_subagent", _tool_invoke_subagent)
        self.register_native("send_to_subagent", _tool_send_to_subagent)

    async def dispatch(self, name: str, args: dict, ctx: Any) -> str:
        """Dispatches tool invocation with permission and stuck-loop checks."""
        # 1. Stuck-Loop Detection
        args_serialized = json.dumps(args, sort_keys=True, default=str)
        call_fingerprint = f"{name}:{args_serialized}"

        ctx.call_history.append(call_fingerprint)
        if len(ctx.call_history) > 10:
            ctx.call_history.pop(0)

        # Count consecutive identical calls
        consecutive_repeats = 1
        for h in reversed(ctx.call_history[:-1]):
            if h == call_fingerprint:
                consecutive_repeats += 1
            else:
                break

        if consecutive_repeats >= 3:
            raise StuckLoopDetected(f"Cognitive loop abort: repeated '{name}' with same parameters {consecutive_repeats} times consecutive.")

        # 2. Permission check
        action_str = self._resolve_action_string(name, args)
        decision = ctx.permissions.resolve(action_str)

        if decision == "deny":
            return json.dumps({"success": False, "error": f"Permission Denied: Action '{action_str}' blocked by policy."})

        if decision == "ask":
            from .bus import MessageBus
            # Trace up to the root parent ID
            root_id = ctx.id
            curr = ctx
            while curr.parent_id:
                # Resolve parent instance from registry of instances
                from .engine import registry_of_instances
                parent_inst = registry_of_instances.get(curr.parent_id)
                if parent_inst:
                    root_id = parent_inst.id
                    curr = parent_inst
                else:
                    break

            bus = MessageBus()
            human_decision = await bus.request_permission(ctx.id, root_id, action_str, args)
            if human_decision != "allow":
                return json.dumps({"success": False, "error": f"Permission Denied: Action '{action_str}' rejected by user."})

        # 3. Execute tool
        try:
            if name in self.native:
                res = await self.native[name](ctx, **args)
                if isinstance(res, ToolResult):
                    return res.to_json()
                return json.dumps({"success": True, "result": str(res)})

            # Simple MCP execution fallback or unknown tool
            return json.dumps({"success": False, "error": f"Tool '{name}' not found."})
        except Exception as e:
            return json.dumps({"success": False, "error": f"Tool execution failed: {str(e)}"})

    def _resolve_action_string(self, name: str, args: dict) -> str:
        if name == "run_command":
            cmd = args.get("command", "")
            # Return e.g. "command(git status)"
            return f"command({cmd})"
        elif name in ("view_file", "write_file"):
            path = args.get("path", "")
            return f"file({path})"
        else:
            return f"tool({name})"


# ---------------------------------------------------------------------------
# Native Tool Implementations
# ---------------------------------------------------------------------------

async def _tool_view_file(ctx: Any, path: str) -> ToolResult:
    """Reads a file relative to the agent's workspace directory."""
    target_path = (ctx.workspace.path / path.lstrip("/")).resolve()

    # Check escape of workspace root path
    try:
        target_path.relative_to(ctx.workspace.path)
    except ValueError:
        return ToolResult(error="Access denied — path escapes workspace.")

    if not target_path.exists():
        return ToolResult(error=f"File '{path}' does not exist.")

    if not target_path.is_file():
        return ToolResult(error=f"'{path}' is a directory, not a file.")

    try:
        content = target_path.read_text(encoding="utf-8")
        # Truncate safe preview
        if len(content) > 8000:
            content = content[:8000] + "\n...[TRUNCATED]..."
        return ToolResult(content=content)
    except Exception as e:
        return ToolResult(error=str(e))


async def _tool_write_file(ctx: Any, path: str, content: str) -> ToolResult:
    """Writes content to a file relative to the agent's workspace directory."""
    target_path = (ctx.workspace.path / path.lstrip("/")).resolve()

    # Check escape of workspace root path
    try:
        target_path.relative_to(ctx.workspace.path)
    except ValueError:
        return ToolResult(error="Access denied — path escapes workspace.")

    # Prevent writing credentials/secrets
    if target_path.name == ".env" or target_path.name.startswith(".env."):
        return ToolResult(error="Writing to environment files is blocked.")

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return ToolResult(content=f"Successfully wrote {len(content)} characters to '{path}'.")
    except Exception as e:
        return ToolResult(error=str(e))


async def _tool_grep_search(ctx: Any, pattern: str) -> ToolResult:
    """Performs light high-performance regex search across the workspace directory."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except Exception as e:
        return ToolResult(error=f"Invalid regex pattern: {e}")

    ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", ".storage"}
    matches = []

    for root, dirs, files in os.walk(ctx.workspace.path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for name in files:
            file_path = Path(root) / name
            try:
                # Don't inspect massive files
                if file_path.stat().st_size > 500_000:
                    continue
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(ctx.workspace.path)
                            matches.append({
                                "file": str(rel_path),
                                "line": i,
                                "match": line.strip()[:150]
                            })
                            if len(matches) >= 50:
                                break
            except Exception:
                continue
            if len(matches) >= 50:
                break
        if len(matches) >= 50:
            break

    return ToolResult(content=json.dumps(matches))


async def _tool_run_command(ctx: Any, command: str) -> ToolResult:
    """Executes a command inside our tiered, secure sandbox environment."""
    sandbox_enabled = ctx.permissions.sandbox_enabled
    res = await execute_sandboxed_command(
        cmd=command,
        cwd=ctx.workspace.path,
        sandbox_enabled=sandbox_enabled,
        network_access=True
    )
    if res["success"]:
        return ToolResult(content=f"Exit Code: {res['exit_code']}\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}")
    else:
        return ToolResult(error=res["stderr"] or f"Exit code {res['exit_code']}")


async def _tool_invoke_subagent(
    ctx: Any,
    role: str,
    prompt: str,
    workspace_mode: str = "inherit",
    model_override: Optional[str] = None
) -> str:
    """Delegation tool. Dynamically spawns a new specialized child subagent."""
    from .engine import invoke_subagent
    child_id = await invoke_subagent(
        caller=ctx,
        role=role,
        prompt=prompt,
        workspace_mode=workspace_mode,
        model_override=model_override
    )
    return f"Spawned subagent '{role}' successfully as ID: {child_id}. You can monitor its progress or communicate via send_to_subagent tool."


async def _tool_send_to_subagent(ctx: Any, child_id: str, message: str) -> str:
    """Communication tool. Sends follow-up message to a spawned child subagent."""
    from .bus import MessageBus
    if child_id not in ctx.children:
        return f"Error: Agent {child_id} is not a subagent of yours."

    bus = MessageBus()
    await bus.send(to=child_id, from_=ctx.id, content=message)
    return f"Message successfully delivered to subagent {child_id}."
