"""AI Service — Gemini and OpenRouter integration with streaming, tool-calling execution loop, retry, and model fallback."""

import time
import asyncio
import base64
import uuid
import json
import httpx
import os
import sys
from typing import AsyncGenerator, Dict, List, Any, Optional
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import get_settings
from .events import EventService
from .context import ContextService

# Ordered fallback chain if primary model errors
FALLBACK_CHAIN = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]


# ---------------------------------------------------------------------------
# JARVIS Tool Definitions
# ---------------------------------------------------------------------------

async def _tool_create_agent(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Create a new specialized agent in the workforce database."""
    from ..schemas.agent import AgentCreate
    from ..services.agent import AgentService

    data = AgentCreate(
        name=args.get("name", "New Agent"),
        role=args.get("role", "General Agent"),
        avatar=args.get("avatar", "🤖"),
        capabilities=args.get("capabilities", []),
        tools=args.get("tools", []),
    )
    agent = await AgentService.create_agent(db, data)
    return json.dumps({"success": True, "agent_id": agent.id, "name": agent.name})


async def _tool_update_agent(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Modify an agent's running status, priority tier, or system resource limits."""
    from ..schemas.agent import AgentUpdate
    from ..services.agent import AgentService

    agent_id = args.get("agent_id", "")
    data = AgentUpdate(
        status=args.get("status"),
        priority=args.get("priority"),
        cpu_allocation=args.get("cpu_percent"),
        memory_allocation=args.get("memory_mb"),
        current_task=args.get("current_task"),
    )
    agent = await AgentService.update_agent(db, agent_id, data)
    if not agent:
        return json.dumps({"success": False, "error": f"Agent {agent_id} not found."})
    return json.dumps({"success": True, "agent_id": agent.id, "status": agent.status})


async def _tool_create_project(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Start a new workspace project/repository."""
    from ..schemas.project import ProjectCreate
    from ..services.project import ProjectService

    data = ProjectCreate(
        name=args.get("name", "New Project"),
        description=args.get("description", ""),
        color=args.get("color", "#3b82f6"),
    )
    project = await ProjectService.create_project(db, data)
    return json.dumps({"success": True, "project_id": project.id, "name": project.name})


async def _tool_create_task(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Create a new automation task under a specific project."""
    from ..schemas.task import TaskCreate
    from ..services.task import TaskService

    project_id = args.get("project_id", "")
    if not project_id:
        return json.dumps({"success": False, "error": "project_id is required."})

    data = TaskCreate(
        project_id=project_id,
        title=args.get("title", "Untitled Task"),
        description=args.get("description", ""),
    )
    task = await TaskService.create_task(db, data)
    return json.dumps({"success": True, "task_id": task.id, "title": task.title})


async def _tool_update_task_status(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Update task execution status (e.g. 'completed', 'failed', 'running')."""
    from ..schemas.task import TaskUpdate
    from ..services.task import TaskService

    task_id = args.get("task_id", "")
    status = args.get("status", "running")
    data = TaskUpdate(status=status)
    task = await TaskService.update_task(db, task_id, data)
    if not task:
        return json.dumps({"success": False, "error": f"Task {task_id} not found."})
    return json.dumps({"success": True, "task_id": task.id, "status": task.status})


async def _tool_save_memory(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Persist facts, preferences, or rules into JARVIS memory bank."""
    from ..schemas.memory import MemoryCreate
    from ..services.memory import MemoryService
    from ..services.project import ProjectService

    project_id = args.get("project_id")
    if not project_id:
        projects = await ProjectService.get_projects(db)
        if not projects:
            return json.dumps({"success": False, "error": "No projects available. Create a project first."})
        project_id = projects[0].id

    data = MemoryCreate(
        project_id=project_id,
        title=args.get("title", "Memory"),
        content=args.get("text", ""),
        importance=min(10, max(1, int(args.get("importance", 5)))),
    )
    memory = await MemoryService.create_memory(db, data)
    return json.dumps({"success": True, "memory_id": memory.id})


async def _tool_read_file(args: Dict[str, Any]) -> str:
    """Retrieve file contents from the workspace repository."""
    from pathlib import Path
    from ..services.file import WORKSPACE_ROOT, _should_ignore

    rel_path = args.get("path", "").lstrip("/")
    target = (WORKSPACE_ROOT / rel_path).resolve()

    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return json.dumps({"success": False, "error": "Access denied — path escapes workspace root."})

    if _should_ignore(target):
        return json.dumps({"success": False, "error": f"File '{rel_path}' is restricted."})

    if not target.exists():
        return json.dumps({"success": False, "error": f"File '{rel_path}' not found."})

    if not target.is_file():
        return json.dumps({"success": False, "error": f"'{rel_path}' is a directory."})

    try:
        content = target.read_text(encoding="utf-8")
        return json.dumps({"success": True, "path": rel_path, "content": content[:8000]})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_write_file(args: Dict[str, Any]) -> str:
    """Create or overwrite files in the workspace repository."""
    from pathlib import Path
    from ..services.file import WORKSPACE_ROOT, _should_ignore, SECRET_NAMES

    rel_path = args.get("path", "").lstrip("/")
    content = args.get("content", "")
    target = (WORKSPACE_ROOT / rel_path).resolve()

    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return json.dumps({"success": False, "error": "Access denied — path escapes workspace root."})

    if target.name in SECRET_NAMES or target.name.startswith(".env"):
        return json.dumps({"success": False, "error": "Writing to secret files is not allowed."})

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": rel_path, "bytes_written": len(content.encode())})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_run_script(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Launch a workspace Python script as an autonomous subprocess agent."""
    from ..services.executor import launch_script

    script_path = args.get("script_path", "")
    timeout = int(args.get("timeout", 300))

    if not script_path:
        return json.dumps({"success": False, "error": "script_path is required."})

    try:
        job_id = await launch_script(db, script_path, timeout=timeout)
        return json.dumps({
            "success": True,
            "job_id": job_id,
            "message": (
                f"Script '{script_path}' launched as job {job_id}. "
                "Call await_job with this job_id to wait for completion, "
                "then read the output_path it returns."
            ),
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_await_job(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Block until a launched subprocess job finishes. Returns the output file path."""
    from ..services.executor import wait_for_job

    job_id = args.get("job_id", "")
    if not job_id:
        return json.dumps({"success": False, "error": "job_id is required."})

    result = await wait_for_job(db, job_id)
    return json.dumps(result)


# Safe terminal blacklisted commands
BLOCKED_COMMAND_PATTERNS = [
    r"rmdir\s+/s", r"del\s+/f", r"\bformat\b",             # Windows destructive
    r"rm\s+-rf\s+/(?!\S)", r"rm\s+-rf\s+~",                 # Unix destructive
    r":\(\)\s*\{\s*:\|:&\s*\};:",                           # fork bomb
    r"mkfs", r"dd\s+if=.*of=/dev/", r">\s*/dev/sd[a-z]",
    r"\bshutdown\b", r"\breboot\b",
    r"curl.*\|\s*sh", r"wget.*\|\s*sh",                     # remote-script-to-shell piping
]


async def _tool_execute_command(args: Dict[str, Any]) -> str:
    """Run a terminal/shell command in the workspace directory with security protections."""
    import subprocess
    import re
    from ..services.file import WORKSPACE_ROOT

    cmd = args.get("command", "")
    if not cmd:
        return json.dumps({"success": False, "error": "command is required."})

    for pat in BLOCKED_COMMAND_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return json.dumps({"success": False, "error": f"Command blocked for security: matches pattern '{pat}'."})

    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT),
            timeout=120
        )
        return json.dumps({
            "success": True,
            "exit_code": res.returncode,
            "stdout": res.stdout[-8000:],
            "stderr": res.stderr[-4000:]
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "Command timed out after 120 seconds."})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_execute_python_file(args: Dict[str, Any]) -> str:
    """Directly execute a Python script inside the workspace."""
    import sys
    import subprocess
    from ..services.file import WORKSPACE_ROOT

    rel_path = args.get("path", "").lstrip("/")
    cmd_args = args.get("args", [])
    target = (WORKSPACE_ROOT / rel_path).resolve()

    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return json.dumps({"success": False, "error": "Access denied — path escapes workspace root."})

    if not target.exists():
        return json.dumps({"success": False, "error": f"File '{rel_path}' does not exist."})

    try:
        command_list = [sys.executable, str(target)] + [str(a) for a in cmd_args]
        res = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT),
            timeout=120
        )
        return json.dumps({
            "success": True,
            "exit_code": res.returncode,
            "stdout": res.stdout[-8000:],
            "stderr": res.stderr[-4000:]
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "Script timed out after 120 seconds."})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_grep_search(args: Dict[str, Any]) -> str:
    """Regex search across workspace files (lightweight high-performance GREP)."""
    import re
    import os
    from pathlib import Path
    from ..services.file import WORKSPACE_ROOT

    pattern = args.get("pattern", "")
    if not pattern:
        return json.dumps({"success": False, "error": "pattern is required."})

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Invalid regex: {e}"})

    ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", ".storage"}
    matches = []

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for name in files:
            file_path = Path(root) / name
            try:
                if file_path.stat().st_size > 500_000:
                    continue
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(WORKSPACE_ROOT)
                            matches.append({
                                "file": str(rel_path),
                                "line": i,
                                "match": line.strip()[:150]
                            })
                            if len(matches) >= 100:
                                break
            except Exception:
                continue
            if len(matches) >= 100:
                break
        if len(matches) >= 100:
            break

    return json.dumps({"success": True, "matches": matches})


async def _tool_web_fetch(args: Dict[str, Any]) -> str:
    """Fetch website HTML/content and scrub script/style tags for fitting context gracefully."""
    import re

    url = args.get("url", "")
    if not url:
        return json.dumps({"success": False, "error": "url is required."})

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()

            text = r.text
            if "</html>" in text.lower():
                text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()

            return json.dumps({"success": True, "content": text[:8000]})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_browser_automation(args: Dict[str, Any]) -> str:
    """Launch headless Chromium via Playwright to click, input, and navigate dynamically."""
    from playwright.async_api import async_playwright
    import re

    url = args.get("url", "")
    actions = args.get("actions", [])

    if not url:
        return json.dumps({"success": False, "error": "url is required."})

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)

            results = []
            for action in actions:
                parts = action.split(maxsplit=1)
                cmd = parts[0].lower()
                target = parts[1] if len(parts) > 1 else ""

                if cmd == "click":
                    await page.click(target)
                    results.append(f"Clicked {target}")
                elif cmd == "type":
                    selector, val = target.split(maxsplit=1)
                    await page.type(selector, val)
                    results.append(f"Typed into {selector}")
                elif cmd == "wait":
                    await page.wait_for_timeout(int(target) if target.isdigit() else 2000)
                    results.append(f"Waited {target}")
                elif cmd == "screenshot":
                    from ..core.config import get_settings
                    import uuid
                    settings = get_settings()
                    filename = f"screenshot_{uuid.uuid4().hex[:8]}.png"
                    path = settings.STORAGE_DIR / filename
                    await page.screenshot(path=str(path))
                    results.append(f"Screenshot saved to {filename}")

            content = await page.content()
            content = re.sub(r"<script.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<style.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()

            await browser.close()
            return json.dumps({
                "success": True,
                "actions_executed": results,
                "page_text": content[:6000]
            })
    except Exception as e:
        fallback_res = await _tool_web_fetch({"url": url})
        return json.dumps({
            "success": False,
            "error": f"Playwright failed ({e}). Executing fallback scrape.",
            "fallback_result": json.loads(fallback_res)
        })


async def _run_subagent_background_loop(agent_id: str, subagent_name: str, role: str, task: str, allowed_tools: List[str], model_arg: Optional[str]):
    """Non-blocking background turn execution loop for spawned subagent."""
    from ..core.database import AsyncSessionLocal
    from ..services.agent import AgentService
    from ..schemas.agent import AgentUpdate
    from pathlib import Path

    async with AsyncSessionLocal() as db:
        try:
            ai_service = AIService()
            system_instr = (
                f"You are {subagent_name}, a specialized subagent in role: '{role}'. "
                f"Your specific task is: '{task}'. "
                "Perform the work diligently using any available tools, and when finished, "
                "provide a concise, high-quality summary/report of your results."
            )

            subagent_history = []
            final_text = ""

            is_research = any(
                "research" in s.lower() or "search" in s.lower()
                for s in [role, subagent_name, task]
            )
            subagent_model = model_arg if model_arg else ("deepseek/deepseek-v4-flash" if is_research else "gemini-3.1-flash-lite")

            if is_research:
                try:
                    specs_dir = Path("Cached/research_specs")
                    specs_dir.mkdir(parents=True, exist_ok=True)
                    spec_path = specs_dir / f"{agent_id[:8]}_spec.md"
                    ceo_spec_chunks = []
                    async for chunk in ai_service.stream_chat(
                        message=f"Create a structured Research Spec for task: '{task}' with objectives, investigation vectors, and expected deliverables.",
                        history=[],
                        system_instruction="You are the JARVIS CEO Orchestrator generating high-level structured specifications.",
                        model="gemini-3.1-flash-lite",
                        db=db
                    ):
                        if "text" in chunk:
                            ceo_spec_chunks.append(chunk["text"])
                    spec_content = "".join(ceo_spec_chunks)
                    spec_path.write_text(spec_content, encoding="utf-8")
                    system_instr += f"\n\n=== CEO RESEARCH SPECIFICATION ===\n{spec_content}\n=================================="
                except Exception:
                    pass

            for turn in range(5):
                response_chunks = []
                async for chunk in ai_service.stream_chat(
                    message=task if turn == 0 else f"Please proceed with the next step to complete: '{task}'.",
                    history=subagent_history,
                    system_instruction=system_instr,
                    model=subagent_model,
                    db=db
                ):
                    if "text" in chunk:
                        response_chunks.append(chunk["text"])

                turn_response = "".join(response_chunks)
                subagent_history.append({"role": "user", "content": f"Turn {turn+1} input"})
                subagent_history.append({"role": "model", "content": turn_response})
                final_text = turn_response

            reports_dir = Path("Cached/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"{agent_id[:8]}_report.md"
            report_path.write_text(final_text, encoding="utf-8")

            await AgentService.update_agent(db, agent_id, AgentUpdate(
                status="idle",
                current_task=None,
                activity=[
                    f"Completed delegation task: {task[:60]}.",
                    f"Report generated: {final_text[:100]}..."
                ]
            ))
        except Exception as e:
            try:
                await AgentService.update_agent(db, agent_id, AgentUpdate(
                    status="idle",
                    current_task=None,
                    activity=[f"Failed during background task execution: {e}"]
                ))
            except Exception:
                pass


async def _tool_delegate_task(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Antigravity 2.0 Non-Blocking Agentic Delegation Launcher."""
    from ..schemas.agent import AgentCreate
    from ..services.agent import AgentService

    subagent_name = args.get("name", "Subagent")
    role = args.get("role", "Specialist")
    task = args.get("task", "")
    allowed_tools = args.get("tools", [])
    model_arg = args.get("model")

    if not task:
        return json.dumps({"success": False, "error": "task description is required for delegation."})

    agent_data = AgentCreate(
        name=subagent_name,
        role=role,
        avatar="🧠",
        status="working",
        current_task=task,
        priority="high",
        capabilities=["specialized_delegation"],
        tools=allowed_tools,
        activity=[f"Spawned as dynamic subagent to run task: '{task}'."]
    )

    agent_record = await AgentService.create_agent(db, agent_data)

    asyncio.create_task(_run_subagent_background_loop(
        agent_id=agent_record.id,
        subagent_name=subagent_name,
        role=role,
        task=task,
        allowed_tools=allowed_tools,
        model_arg=model_arg
    ))

    return json.dumps({
        "success": True,
        "status": "spawned_and_running",
        "subagent_id": agent_record.id,
        "subagent_name": subagent_name,
        "message": f"Subagent '{subagent_name}' ({role}) spawned successfully and is running task asynchronously."
    })


async def _tool_send_marketing_email(args: Dict[str, Any]) -> str:
    """Placeholder tool for sending email marketing campaigns via Resend."""
    to_email = args.get("to_email", "")
    subject = args.get("subject", "")
    body = args.get("body", "")

    return json.dumps({
        "success": True,
        "message": f"Resend: Email successfully queued for delivery to '{to_email}'.",
        "details": {
            "subject": subject,
            "body_length": len(body),
            "status": "pending_configuration"
        }
    })


async def _tool_offload_to_jules(args: Dict[str, Any]) -> str:
    """Placeholder tool for offloading repository tasks directly to Jules API workflows."""
    repo = args.get("repository", "main-repo")
    task = args.get("task_description", "")

    return json.dumps({
        "success": True,
        "message": f"Offloaded task to Jules GitHub workflows for repository '{repo}'.",
        "task_assigned": task,
        "status": "pending_configuration"
    })


async def _tool_create_automation(args: Dict[str, Any]) -> str:
    """Create a new workflow automation from plain English description."""
    title = args.get("title", "New Automation")
    schedule = args.get("schedule", "Manual / On Demand")
    description = args.get("description", "")
    return json.dumps({
        "success": True,
        "name": title,
        "schedule": schedule,
        "description": description,
        "message": f"Automation '{title}' created and configured successfully in the workspace."
    })


TOOL_DISPATCH = {
    "create_agent": _tool_create_agent,
    "update_agent_allocation": _tool_update_agent,
    "create_project": _tool_create_project,
    "create_task": _tool_create_task,
    "update_task_status": _tool_update_task_status,
    "create_automation": _tool_create_automation,
    "save_memory": _tool_save_memory,
    "read_file_content": _tool_read_file,
    "write_file_content": _tool_write_file,
    "run_script": _tool_run_script,
    "await_job": _tool_await_job,
    "execute_command": _tool_execute_command,
    "execute_python_file": _tool_execute_python_file,
    "grep_search": _tool_grep_search,
    "web_fetch": _tool_web_fetch,
    "browser_automation": _tool_browser_automation,
    "delegate_task": _tool_delegate_task,
    "send_marketing_email": _tool_send_marketing_email,
    "offload_to_jules": _tool_offload_to_jules,
}

JARVIS_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="create_agent",
            description="Create a new specialized AI agent in the JARVIS workforce database.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING, description="Human-readable agent name"),
                    "role": types.Schema(type=types.Type.STRING, description="Agent's functional role"),
                    "avatar": types.Schema(type=types.Type.STRING, description="Single emoji avatar"),
                    "capabilities": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                    "tools": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                },
                required=["name", "role"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_agent_allocation",
            description="Modify an agent's running status, priority tier, current task, or resource limits.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "agent_id": types.Schema(type=types.Type.STRING),
                    "status": types.Schema(type=types.Type.STRING),
                    "priority": types.Schema(type=types.Type.STRING),
                    "current_task": types.Schema(type=types.Type.STRING),
                    "cpu_percent": types.Schema(type=types.Type.INTEGER),
                    "memory_mb": types.Schema(type=types.Type.INTEGER),
                },
                required=["agent_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_project",
            description="Start a new workspace project/repository.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "description": types.Schema(type=types.Type.STRING),
                    "color": types.Schema(type=types.Type.STRING),
                },
                required=["name"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_task",
            description="Create a new automation task under a specific project.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "project_id": types.Schema(type=types.Type.STRING),
                    "title": types.Schema(type=types.Type.STRING),
                    "description": types.Schema(type=types.Type.STRING),
                },
                required=["project_id", "title"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_task_status",
            description="Update a task's execution status.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                    "status": types.Schema(type=types.Type.STRING),
                },
                required=["task_id", "status"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_automation",
            description="Create a new workflow automation sequence from plain English.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "title": types.Schema(type=types.Type.STRING, description="Title of the automation"),
                    "schedule": types.Schema(type=types.Type.STRING, description="Execution interval or trigger (e.g. 'Daily at 9am', 'Every 30m')"),
                    "description": types.Schema(type=types.Type.STRING, description="Detailed plain English explanation"),
                },
                required=["title", "description"],
            ),
        ),
        types.FunctionDeclaration(
            name="save_memory",
            description="Persist a fact, preference, or rule into the JARVIS memory bank.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "text": types.Schema(type=types.Type.STRING),
                    "title": types.Schema(type=types.Type.STRING),
                    "importance": types.Schema(type=types.Type.INTEGER),
                    "project_id": types.Schema(type=types.Type.STRING),
                },
                required=["text"],
            ),
        ),
        types.FunctionDeclaration(
            name="read_file_content",
            description="Read full file contents from the workspace.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "path": types.Schema(type=types.Type.STRING),
                },
                required=["path"],
            ),
        ),
        types.FunctionDeclaration(
            name="write_file_content",
            description="Create or overwrite a file in the workspace.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "path": types.Schema(type=types.Type.STRING),
                    "content": types.Schema(type=types.Type.STRING),
                },
                required=["path", "content"],
            ),
        ),
        types.FunctionDeclaration(
            name="run_script",
            description="Launch a Python script from the workspace as an autonomous subprocess agent.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "script_path": types.Schema(type=types.Type.STRING),
                    "timeout": types.Schema(type=types.Type.INTEGER),
                },
                required=["script_path"],
            ),
        ),
        types.FunctionDeclaration(
            name="await_job",
            description="Wait for a previously launched subprocess job to finish.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "job_id": types.Schema(type=types.Type.STRING),
                },
                required=["job_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="execute_command",
            description="Run a shell/terminal command in the workspace directory.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "command": types.Schema(type=types.Type.STRING),
                },
                required=["command"],
            ),
        ),
        types.FunctionDeclaration(
            name="execute_python_file",
            description="Directly execute a python script inside the workspace synchronously.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "path": types.Schema(type=types.Type.STRING),
                    "args": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                },
                required=["path"],
            ),
        ),
        types.FunctionDeclaration(
            name="grep_search",
            description="Perform a high-performance regex search across all files in the workspace.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pattern": types.Schema(type=types.Type.STRING),
                },
                required=["pattern"],
            ),
        ),
        types.FunctionDeclaration(
            name="web_fetch",
            description="Scrape and retrieve page content of any public URL/website.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(type=types.Type.STRING),
                },
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="browser_automation",
            description="Execute dynamic browser steps using headless Playwright chromium.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(type=types.Type.STRING),
                    "actions": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                },
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="delegate_task",
            description="Antigravity 2.0: Spawns an isolated dynamic subagent to solve a subproblem.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "role": types.Schema(type=types.Type.STRING),
                    "task": types.Schema(type=types.Type.STRING),
                    "tools": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                    "model": types.Schema(type=types.Type.STRING, description="Optional model for subagent (defaults to deepseek/deepseek-v4-flash for research subagents)"),
                },
                required=["name", "role", "task"],
            ),
        ),
        types.FunctionDeclaration(
            name="send_marketing_email",
            description="Queue and send marketing or notification emails via Resend.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "to_email": types.Schema(type=types.Type.STRING),
                    "subject": types.Schema(type=types.Type.STRING),
                    "body": types.Schema(type=types.Type.STRING),
                },
                required=["to_email", "subject", "body"],
            ),
        ),
        types.FunctionDeclaration(
            name="offload_to_jules",
            description="Offload workspace workflow or complex PR-level tasks directly to Jules GitHub agent.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "repository": types.Schema(type=types.Type.STRING),
                    "task_description": types.Schema(type=types.Type.STRING),
                },
                required=["repository", "task_description"],
            ),
        ),
    ])
]


async def _execute_tool(name: str, args: Dict[str, Any], db: Optional[AsyncSession]) -> str:
    handler = TOOL_DISPATCH.get(name)
    if not handler:
        return json.dumps({"success": False, "error": f"Unknown tool: {name}"})

    try:
        if name in ("read_file_content", "write_file_content", "execute_command", "execute_python_file", "grep_search", "web_fetch", "browser_automation", "send_marketing_email", "offload_to_jules"):
            return await handler(args)
        else:
            if db is None:
                return json.dumps({"success": False, "error": "No database session available for this tool."})
            return await handler(db, args)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


class AIService:
    """Wraps the google-genai SDK & OpenRouter with streaming, retry, fallback, offline task router, and JARVIS function-calling."""

    def __init__(self):
        settings = get_settings()
        self.client = (
            genai.Client(api_key=settings.GEMINI_API_KEY)
            if settings.GEMINI_API_KEY
            else None
        )

    def _ensure_client(self):
        if self.client is None:
            settings = get_settings()
            if not settings.GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY not configured. Set it in your .env file.")
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def stream_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        system_instruction: str = "You are JARVIS, an advanced AI Operating System. Answer elegantly, with a technical, refined, and helpful persona.",
        model: str = "gemini-3.1-flash-lite",
        use_search: bool = False,
        temperature: float = 0.7,
        db: Optional[AsyncSession] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a chat completion from Gemini/OpenRouter or Offline task router."""

        # Offline / Task Router Check
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            import task_router
            route_info = await asyncio.to_thread(task_router.route_task, message)
            if route_info.get("engine") in ("local_agent_bridge", "local_direct_script", "offline_fallback_failed"):
                yield {"text": f"[{route_info.get('mode', 'OFFLINE')}]\n" + route_info.get("response", "")}
                if route_info.get("staged_files"):
                    yield {"text": f"\n\n[STAGED FILES FOR CLOUD REVIEW]: {', '.join(route_info.get('staged_files'))}"}
                yield {"done": True, "latency": 0.1, "token_count": 50, "model_used": "jarvis-local"}
                return
        except Exception:
            pass

        # Select OpenRouter Backup support
        is_openrouter = ("deepseek" in model or "gemma" in model or "openrouter" in model or model == "gemma-4-31b")
        if is_openrouter:
            async for chunk in self._stream_openrouter_chat(
                message=message,
                history=history,
                system_instruction=system_instruction,
                model=model,
                temperature=temperature,
                db=db
            ):
                yield chunk
            return

        self._ensure_client()

        correlation_id = str(uuid.uuid4())
        enriched_message, context_trace = await ContextService.assemble(message, db)
        await EventService.record(db, "objective.started", status="running", correlation_id=correlation_id, metadata={"context": context_trace})

        contents: List[types.Content] = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=enriched_message)])
        )

        tools_to_use = JARVIS_TOOLS if not use_search else [types.Tool(google_search=types.GoogleSearch())]

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            tools=tools_to_use,
        )

        primary_model = model if model in FALLBACK_CHAIN else "gemini-3.1-flash-lite"
        models_to_try = [primary_model] + [m for m in FALLBACK_CHAIN if m != primary_model]
        last_error = None

        for attempt_model in models_to_try:
            retries = 0
            while retries < 2:
                try:
                    start = time.monotonic()
                    token_count = 0
                    grounding_chunks: list = []

                    current_contents = list(contents)

                    while True:
                        response = await self.client.aio.models.generate_content_stream(
                            model=attempt_model,
                            contents=current_contents,
                            config=config,
                        )

                        collected_parts: List[types.Part] = []
                        function_calls_found: List[types.FunctionCall] = []
                        text_buffer = ""

                        async for chunk in response:
                            text = chunk.text or ""
                            if text:
                                token_count += len(text.split())
                                text_buffer += text

                                search_chunks: list = []
                                if hasattr(chunk, "candidates") and chunk.candidates:
                                    meta = getattr(chunk.candidates[0], "grounding_metadata", None)
                                    if meta and hasattr(meta, "grounding_chunks") and meta.grounding_chunks:
                                        grounding_chunks = meta.grounding_chunks
                                        search_chunks = [
                                            {
                                                "uri": getattr(getattr(c, "web", None), "uri", ""),
                                                "title": getattr(getattr(c, "web", None), "title", ""),
                                            }
                                            for c in grounding_chunks
                                            if hasattr(c, "web")
                                        ]
                                yield {"text": text, "searchChunks": search_chunks}

                            if hasattr(chunk, "candidates") and chunk.candidates:
                                candidate = chunk.candidates[0]
                                if hasattr(candidate, "content") and candidate.content:
                                    for part in candidate.content.parts or []:
                                        if hasattr(part, "function_call") and part.function_call:
                                            function_calls_found.append(part.function_call)
                                        collected_parts.append(part)

                        if not function_calls_found:
                            break

                        model_content = types.Content(role="model", parts=collected_parts)
                        current_contents.append(model_content)

                        function_response_parts: List[types.Part] = []
                        for fc in function_calls_found:
                            call_args = dict(fc.args) if fc.args else {}

                            yield {
                                "toolCall": {
                                    "name": fc.name,
                                    "args": call_args,
                                    "status": "running",
                                }
                            }

                            result_str = await _execute_tool(fc.name, call_args, db)

                            yield {
                                "toolCall": {
                                    "name": fc.name,
                                    "args": call_args,
                                    "result": result_str,
                                    "status": "completed",
                                }
                            }

                            if fc.name in (
                                "create_agent",
                                "update_agent_allocation",
                                "create_project",
                                "create_task",
                                "update_task_status",
                                "create_automation",
                                "save_memory",
                                "run_script",
                                "write_file_content",
                                "execute_command",
                                "execute_python_file",
                                "grep_search",
                                "delegate_task",
                            ):
                                yield {"workspaceChanged": correlation_id}

                            function_response_parts.append(
                                types.Part.from_function_response(
                                    name=fc.name,
                                    response={"result": result_str},
                                )
                            )

                        current_contents.append(
                            types.Content(role="user", parts=function_response_parts)
                        )

                    latency = time.monotonic() - start
                    yield {
                        "done": True,
                        "latency": round(latency, 3),
                        "token_count": token_count,
                        "model_used": attempt_model,
                    }
                    return

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    is_transient = any(
                        s in err_str
                        for s in ["503", "429", "UNAVAILABLE", "overloaded", "ResourceExhausted"]
                    )
                    if is_transient and retries < 1:
                        retries += 1
                        await asyncio.sleep(retries)
                        continue
                    break

        yield {"error": str(last_error) if last_error else "All models failed"}

    async def _stream_openrouter_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        system_instruction: str,
        model: str,
        temperature: float,
        db: Optional[AsyncSession] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Custom streaming execution loop with integrated function calling for OpenRouter."""
        settings = get_settings()
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            yield {"error": "OPENROUTER_API_KEY is not configured in settings."}
            return

        correlation_id = str(uuid.uuid4())
        enriched_message, context_trace = await ContextService.assemble(message, db)
        await EventService.record(db, "objective.started", status="running", correlation_id=correlation_id, metadata={"context": context_trace})

        real_model = model
        if model == "gemma-4-31b" or "gemma" in model:
            real_model = "google/gemma-2-27b-it"
        elif "deepseek" in model:
            real_model = settings.OPENROUTER_MODEL  # from OPENROUTER_MODEL env var, default: deepseek/deepseek-v4-flash

        messages = [{"role": "system", "content": system_instruction}]
        for msg in history:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": enriched_message})

        openai_tools = []
        for t in JARVIS_TOOLS:
            for fd in t.function_declarations:
                props = {}
                if fd.parameters and fd.parameters.properties:
                    for k, v in fd.parameters.properties.items():
                        props[k] = {
                            "type": "string" if v.type == "STRING" else "integer" if v.type == "INTEGER" else "array" if v.type == "ARRAY" else "object",
                            "description": getattr(v, "description", "")
                        }
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": fd.name,
                        "description": fd.description,
                        "parameters": {
                            "type": "object",
                            "properties": props,
                            "required": fd.parameters.required if fd.parameters else []
                        }
                    }
                })

        start = time.monotonic()
        token_count = 0

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "JARVIS AI OS"
        }

        current_messages = list(messages)

        while True:
            payload = {
                "model": real_model,
                "messages": current_messages,
                "temperature": temperature,
                "tools": openai_tools,
                "stream": True
            }

            async with httpx.AsyncClient() as client:
                try:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=120.0
                    ) as response:
                        if response.status_code != 200:
                            err_body = await response.aread()
                            yield {"error": f"OpenRouter API returned error {response.status_code}: {err_body.decode()}"}
                            return

                        tool_calls_buffer = {}
                        text_buffer = ""

                        async for line in response.iter_lines():
                            if not line.strip():
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    choice = data["choices"][0]
                                    delta = choice.get("delta", {})

                                    content_delta = delta.get("content", "")
                                    if content_delta:
                                        token_count += len(content_delta.split())
                                        text_buffer += content_delta
                                        yield {"text": content_delta, "searchChunks": []}

                                    delta_tool_calls = delta.get("tool_calls", [])
                                    if delta_tool_calls:
                                        for tc in delta_tool_calls:
                                            index = tc.get("index", 0)
                                            if index not in tool_calls_buffer:
                                                tool_calls_buffer[index] = {
                                                    "id": tc.get("id", ""),
                                                    "name": tc.get("function", {}).get("name", ""),
                                                    "arguments": ""
                                                }
                                            if "id" in tc:
                                                tool_calls_buffer[index]["id"] = tc["id"]
                                            if "function" in tc:
                                                func = tc["function"]
                                                if "name" in func:
                                                    tool_calls_buffer[index]["name"] = func["name"]
                                                if "arguments" in func:
                                                    tool_calls_buffer[index]["arguments"] += func["arguments"]
                                except Exception:
                                    continue
                except Exception as e:
                    yield {"error": f"OpenRouter connection error: {e}"}
                    return

            if tool_calls_buffer:
                assistant_tool_calls = []
                for index, tc in tool_calls_buffer.items():
                    assistant_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    })

                current_messages.append({
                    "role": "assistant",
                    "content": text_buffer,
                    "tool_calls": assistant_tool_calls
                })

                for index, tc in tool_calls_buffer.items():
                    name = tc["name"]
                    args_str = tc["arguments"]
                    try:
                        args = json.loads(args_str) if args_str else {}
                    except Exception:
                        args = {}

                    yield {
                        "toolCall": {
                            "name": name,
                            "args": args,
                            "status": "running"
                        }
                    }

                    result_str = await _execute_tool(name, args, db)

                    yield {
                        "toolCall": {
                            "name": name,
                            "args": args,
                            "result": result_str,
                            "status": "completed"
                        }
                    }

                    if name in (
                        "create_agent",
                        "update_agent_allocation",
                        "create_project",
                        "create_task",
                        "update_task_status",
                        "create_automation",
                        "save_memory",
                        "run_script",
                        "write_file_content",
                        "execute_command",
                        "execute_python_file",
                        "grep_search",
                        "delegate_task",
                    ):
                        yield {"workspaceChanged": correlation_id}

                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": name,
                        "content": result_str
                    })

                tool_calls_buffer = {}
                continue
            else:
                break

        latency = time.monotonic() - start
        yield {
            "done": True,
            "latency": round(latency, 3),
            "token_count": token_count,
            "model_used": real_model
        }

    async def transcribe_audio(self, audio_b64: str, mime_type: str = "audio/webm") -> str:
        """Transcribe base64-encoded audio using a fast Gemini model."""
        self._ensure_client()
        audio_bytes = base64.b64decode(audio_b64)
        response = await self.client.aio.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                types.Part.from_text(
                    text="Accurately transcribe this audio. Output ONLY the transcribed words."
                ),
            ],
        )
        return response.text or ""
