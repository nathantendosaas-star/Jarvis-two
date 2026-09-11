import os
import sys
import re
import json
import subprocess
import requests
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "jarvis-local")
TEMPERATURE = 0.1

MAX_STEPS = 15
STUCK_REPEAT_LIMIT = 3
MAX_FILE_READ_CHARS = 8000
MAX_TOOL_OUTPUT_CHARS = 4000
COMMAND_TIMEOUT = 30

AUTO_APPROVE_COMMANDS = True

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
STAGED_DIR = os.path.join(WORKSPACE_DIR, ".staged_offline_changes")
LOG_FILE = os.path.join(WORKSPACE_DIR, ".jarvis_log.jsonl")

BLOCKED_COMMAND_PATTERNS = [
    r"rmdir\s+/s", r"del\s+/f", r"\bformat\b",             # Windows destructive
    r"rm\s+-rf\s+/(?!\S)", r"rm\s+-rf\s+~",                 # Unix destructive
    r":\(\)\s*\{\s*:\|:&\s*\};:",                           # fork bomb
    r"mkfs", r"dd\s+if=.*of=/dev/", r">\s*/dev/sd[a-z]",
    r"\bshutdown\b", r"\breboot\b",
    r"curl.*\|\s*sh", r"wget.*\|\s*sh",                     # remote-script-to-shell piping
]

SAFE_COMMAND_PREFIXES = (
    "ls", "dir", "cat", "type", "pwd", "echo", "git status", "git diff", "git log",
    "python", "python3", "pip", "pip3", "npm", "node", "npx", "pytest",
    "mkdir", "grep", "findstr", "wc", "head", "tail",
)


def safe_path(filename, target_dir=WORKSPACE_DIR):
    """Resolve a filename and guarantee it stays inside target_dir."""
    filepath = os.path.abspath(os.path.join(target_dir, filename))
    if os.path.commonpath([filepath, target_dir]) != target_dir:
        raise ValueError(f"Path escapes directory, refusing: {filename}")
    return filepath


def log_event(event: dict):
    event["ts"] = datetime.utcnow().isoformat() + "Z"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def load_manifest() -> dict:
    """Loads .staged_offline_changes/manifest.json."""
    manifest_path = os.path.join(STAGED_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"staged_at": "", "files": []}


def apply_staged_file(original_rel_path: str) -> str:
    """Copies a staged file into the real workspace location and removes it from the manifest."""
    manifest = load_manifest()
    files = manifest.get("files", [])
    entry = next((f for f in files if f.get("original_path") == original_rel_path or f.get("filename") == original_rel_path), None)
    
    staged_path = os.path.join(WORKSPACE_DIR, entry.get("staged_path")) if entry else os.path.join(STAGED_DIR, original_rel_path)
    real_path = safe_path(original_rel_path)
    
    if not os.path.exists(staged_path):
        return f"Error: staged file {staged_path} does not exist."
    
    try:
        os.makedirs(os.path.dirname(real_path), exist_ok=True)
        with open(staged_path, "r", encoding="utf-8") as sf:
            content = sf.read()
        with open(real_path, "w", encoding="utf-8") as rf:
            rf.write(content)
        
        try:
            os.remove(staged_path)
        except Exception:
            pass
        
        if entry and entry in files:
            files.remove(entry)
            manifest["files"] = files
            manifest_path = os.path.join(STAGED_DIR, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2)
                
        return f"Applied {original_rel_path} to workspace successfully."
    except Exception as e:
        return f"Error applying {original_rel_path}: {str(e)}"


def discard_staged_file(original_rel_path: str) -> str:
    """Deletes a staged file and cleans up the manifest."""
    manifest = load_manifest()
    files = manifest.get("files", [])
    entry = next((f for f in files if f.get("original_path") == original_rel_path or f.get("filename") == original_rel_path), None)
    
    staged_path = os.path.join(WORKSPACE_DIR, entry.get("staged_path")) if entry else os.path.join(STAGED_DIR, original_rel_path)
    
    if os.path.exists(staged_path):
        try:
            os.remove(staged_path)
        except Exception:
            pass
            
    if entry and entry in files:
        files.remove(entry)
        manifest["files"] = files
        manifest_path = os.path.join(STAGED_DIR, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)
            
    return f"Discarded staged file {original_rel_path}."


def record_staged_file(filename, original_content, new_content, task_description="Local task"):
    """Records a file change to .staged_offline_changes and updates manifest.json."""
    os.makedirs(STAGED_DIR, exist_ok=True)
    staged_filepath = safe_path(filename, STAGED_DIR)
    os.makedirs(os.path.dirname(staged_filepath), exist_ok=True)

    with open(staged_filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    manifest = load_manifest()
    if not manifest.get("staged_at"):
        manifest["staged_at"] = datetime.utcnow().isoformat() + "Z"

    existing = next((item for item in manifest.get("files", []) if item.get("filename") == filename), None)
    file_record = {
        "filename": filename,
        "original_path": os.path.relpath(safe_path(filename, WORKSPACE_DIR), WORKSPACE_DIR),
        "staged_path": os.path.relpath(staged_filepath, WORKSPACE_DIR),
        "task": task_description,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if existing:
        manifest["files"].remove(existing)
    manifest.setdefault("files", []).append(file_record)

    manifest_path = os.path.join(STAGED_DIR, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)


# =============================================================================
# TOOLS
# =============================================================================

def list_directory(path="."):
    """Lists files in the project folder."""
    try:
        target = safe_path(path)
        ignore = {".git", "node_modules", "__pycache__", "venv", ".venv", ".jarvis_log.jsonl", ".staged_offline_changes"}
        entries = []
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in ignore]
            for name in files + dirs:
                if name in ignore:
                    continue
                rel = os.path.relpath(os.path.join(root, name), WORKSPACE_DIR)
                entries.append(rel)
            if len(entries) > 300:
                entries.append("...[truncated, too many files]...")
                break
        return "Files in project folder:\n" + "\n".join(sorted(entries)) if entries else "(empty)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def read_file(filename, staging=True):
    """Reads the contents of a file inside the project folder."""
    try:
        if staging:
            staged_path = os.path.join(STAGED_DIR, filename)
            if os.path.exists(staged_path):
                with open(staged_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                return f"--- CONTENT OF {filename} (STAGED) ---\n{content}"

        filepath = safe_path(filename)
        if not os.path.exists(filepath):
            return f"Error: {filename} does not exist."
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if len(content) > MAX_FILE_READ_CHARS:
            content = content[:MAX_FILE_READ_CHARS] + f"\n...[TRUNCATED, {len(content)} chars total]..."
        return f"--- CONTENT OF {filename} ---\n{content}"
    except Exception as e:
        return f"Error reading file {filename}: {str(e)}"


def write_file(filename, content, task_description="Offline task", staging=True):
    """Creates or overwrites a file. In staging mode, writes to .staged_offline_changes."""
    try:
        filepath = safe_path(filename)
        orig_content = ""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    orig_content = f.read()
            except Exception:
                pass

        if staging:
            record_staged_file(filename, orig_content, content, task_description)
            return f"Success: staged {len(content)} chars to '.staged_offline_changes/{filename}' awaiting cloud model review."
        else:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Success: wrote {len(content)} chars to '{filename}'."
    except Exception as e:
        return f"Error writing to file {filename}: {str(e)}"


def edit_file(filename, old, new="", task_description="Offline edit", staging=True):
    """Find-and-replace edit."""
    try:
        staged_filepath = os.path.join(STAGED_DIR, filename)
        target_filepath = safe_path(filename)

        text = ""
        if staging and os.path.exists(staged_filepath):
            with open(staged_filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        elif os.path.exists(target_filepath):
            with open(target_filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            return f"Error: {filename} does not exist. Use write_file to create it first."

        if old == "":
            return "Error: 'old' cannot be empty."
        count = text.count(old)
        if count == 0:
            return "Error: old text not found in file (must match exactly, including whitespace)."
        if count > 1:
            return f"Error: old text appears {count} times, not unique. Add more surrounding context."

        new_text = text.replace(old, new, 1)

        if staging:
            record_staged_file(filename, text, new_text, task_description)
            return f"Success: staged edited '{filename}' in .staged_offline_changes/ for cloud model review."
        else:
            with open(target_filepath, 'w', encoding='utf-8') as f:
                f.write(new_text)
            return f"Success: edited '{filename}'."
    except Exception as e:
        return f"Error editing file {filename}: {str(e)}"


def search_files(pattern, path="."):
    """Regex search across files in the project folder."""
    try:
        root = safe_path(path)
        regex = re.compile(pattern)
    except re.error as e:
        return f"Error: invalid regex: {e}"
    except Exception as e:
        return f"Error: {e}"

    ignore = {".git", "node_modules", "__pycache__", "venv", ".venv", ".staged_offline_changes"}
    matches = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore]
        for name in files:
            fpath = os.path.join(dirpath, name)
            try:
                if os.path.getsize(fpath) > 500_000:
                    continue
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = os.path.relpath(fpath, WORKSPACE_DIR)
                            matches.append(f"{rel}:{i}: {line.strip()[:200]}")
                            if len(matches) >= 100:
                                break
            except Exception:
                continue
            if len(matches) >= 100:
                break
        if len(matches) >= 100:
            break
    return "\n".join(matches) if matches else "No matches found."


def execute_command(command):
    """Executes a terminal/shell command inside the project folder."""
    for pat in BLOCKED_COMMAND_PATTERNS:
        if re.search(pat, command, re.IGNORECASE):
            return f"Error: command blocked for system safety (matched: {pat})."

    is_safe_prefix = any(command.strip().lower().startswith(p) for p in SAFE_COMMAND_PREFIXES)
    if not AUTO_APPROVE_COMMANDS and not is_safe_prefix:
        print(f"\n[CONFIRM] Agent wants to run: {command}")
        resp = input("Allow? [y/N]: ").strip().lower()
        if resp != "y":
            return "Denied: user did not approve this command."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT
        )
        output = result.stdout[-MAX_TOOL_OUTPUT_CHARS:] if result.stdout else ""
        error = result.stderr[-MAX_TOOL_OUTPUT_CHARS:] if result.stderr else ""
        return f"Exit Code: {result.returncode}\nSTDOUT:\n{output}\nSTDERR:\n{error}"
    except subprocess.TimeoutExpired:
        return f"Error: command execution timed out ({COMMAND_TIMEOUT}s limit)."
    except Exception as e:
        return f"Error executing command: {str(e)}"


TOOLS = {
    "list_directory": list_directory,
    "search_files": search_files,
    "execute_command": execute_command,
}

SYSTEM_PROMPT = f"""You are JARVIS, a highly capable local agent working inside the project folder: {WORKSPACE_DIR}
You can think, plan, and execute simple actions using tools.

You have access to the following tools:
- list_directory() -> Returns files in the current workspace.
- read_file(filename) -> Reads file contents.
- search_files(pattern) -> Regex search across all files in the workspace.
- write_file(filename) -> Creates/overwrites a file. Give the content in a CONTENT block.
- edit_file(filename) -> Finds exact text in a file and replaces it. Give the text in OLD/NEW blocks.
- execute_command(command) -> Runs a shell command in the workspace.

You must operate in a strict loop: Thought, Action, Arguments, Observation.

FORMAT A - for list_directory, read_file, search_files, execute_command:
Thought: what you need to do next
Action: tool_name
Arguments: {{"key": "value"}}
Observation: [the system fills this in]

FORMAT B - for write_file:
Thought: what you need to do next
Action: write_file
Arguments: {{"filename": "path/to/file.py"}}
Content:
<<<START>>>
full file content goes here
<<<END>>>
Observation: [the system fills this in]

FORMAT C - for edit_file:
Thought: what you need to do next
Action: edit_file
Arguments: {{"filename": "path/to/file.py"}}
Old:
<<<START>>>
exact existing text to find
<<<END>>>
New:
<<<START>>>
replacement text
<<<END>>>
Observation: [the system fills this in]

RULES:
- Take exactly ONE action per response, then stop and wait for Observation.
- All file writes and edits will be automatically staged in .staged_offline_changes/ for cloud model review.
- Filenames are relative to project folder.
- Once finished, output: Final Answer: [summary of what was accomplished]
"""


def query_ollama(prompt_history):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt_history,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        return response.json().get("response", "")
    except Exception as e:
        print(f"Connection Error to Ollama ({OLLAMA_URL}): {e}")
        return ""


def extract_block(text, start_marker="<<<START>>>", end_marker="<<<END>>>"):
    if start_marker not in text:
        return None
    body = text.split(start_marker, 1)[1]
    if end_marker in body:
        return body.split(end_marker, 1)[0].strip("\n")
    return body.strip("\n")


def parse_response(response):
    action_match = re.search(r"Action:\s*(\w+)", response)
    args_match = re.search(r"Arguments:\s*(\{.*?\})", response, re.DOTALL)

    if not action_match:
        return None, None, None, None, None, "Could not find an Action field."

    tool_name = action_match.group(1).strip()

    args = {}
    if args_match:
        try:
            args = json.loads(args_match.group(1))
        except json.JSONDecodeError as e:
            return tool_name, None, None, None, None, f"Arguments were not valid JSON: {e}"

    if tool_name == "write_file":
        content = extract_block(response)
        if content is None:
            return tool_name, args, None, None, None, "write_file requires a Content block with <<<START>>>...<<<END>>>."
        return tool_name, args, content, None, None, None

    if tool_name == "edit_file":
        old_section = response.split("Old:", 1)[1] if "Old:" in response else None
        new_section = response.split("New:", 1)[1] if "New:" in response else None
        old = extract_block(old_section) if old_section else None
        new = extract_block(new_section) if new_section else ""
        if old is None:
            return tool_name, args, None, None, None, "edit_file requires an Old block with <<<START>>>...<<<END>>>."
        return tool_name, args, None, old, new, None

    return tool_name, args, None, None, None, None


def run_agentic_workflow(user_goal, conversation_history="", staging=True):
    print(f"\n🚀 Starting Local Agentic Workflow: '{user_goal}'")

    active_history = f"{SYSTEM_PROMPT}\n{conversation_history}\nUser Goal: {user_goal}\n"

    final_answer = "No final answer was reached."
    recent_fingerprints = []
    staged_files = []

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- [Step {step}] Thinking... ---")

        response = query_ollama(active_history)

        if not response.strip():
            print("⚠️ Empty response from Ollama model.")
            break

        active_history += response + "\n"

        if "Final Answer:" in response:
            match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL)
            final_answer = match.group(1).strip() if match else response
            log_event({"goal": user_goal, "step": step, "final_answer": final_answer})
            break

        tool_name, args, content, old, new, parse_error = parse_response(response)

        if parse_error:
            observation = f"Error: {parse_error} Please respond using exact tool format."
        elif tool_name not in TOOLS and tool_name not in ("write_file", "edit_file", "read_file"):
            observation = f"Error: Tool '{tool_name}' does not exist."
        else:
            fingerprint = json.dumps({"tool": tool_name, "args": args, "content": content, "old": old}, sort_keys=True, default=str)
            recent_fingerprints.append(fingerprint)
            if len(recent_fingerprints) > STUCK_REPEAT_LIMIT:
                recent_fingerprints.pop(0)
            if len(recent_fingerprints) == STUCK_REPEAT_LIMIT and len(set(recent_fingerprints)) == 1:
                final_answer = "Task aborted: agent got stuck repeating the same action."
                log_event({"goal": user_goal, "aborted": "stuck_loop"})
                break

            print(f"🔧 Tool [{tool_name}]...")
            try:
                if tool_name == "read_file":
                    fn = args.get("filename") or args.get("path") or ""
                    observation = read_file(filename=fn, staging=staging)
                elif tool_name == "write_file":
                    fn = args.get("filename") or args.get("path") or ""
                    observation = write_file(filename=fn, content=content, task_description=user_goal, staging=staging)
                    if fn not in staged_files:
                        staged_files.append(fn)
                elif tool_name == "edit_file":
                    fn = args.get("filename") or args.get("path") or ""
                    observation = edit_file(filename=fn, old=old, new=new, task_description=user_goal, staging=staging)
                    if fn not in staged_files:
                        staged_files.append(fn)
                else:
                    observation = TOOLS[tool_name](**args) if isinstance(args, dict) else TOOLS[tool_name](args)
            except Exception as e:
                observation = f"Error executing tool: {str(e)}"

        if len(observation) > MAX_TOOL_OUTPUT_CHARS:
            observation = observation[:MAX_TOOL_OUTPUT_CHARS] + "\n...[TRUNCATED]..."

        active_history += f"Observation: {observation}\n"
        log_event({"goal": user_goal, "step": step, "tool": tool_name, "observation": observation[:1000]})

    return {
        "status": "completed" if "Final Answer:" in active_history else "failed",
        "final_answer": final_answer,
        "staged_files": staged_files,
        "history": active_history
    }


async def stream_agentic_workflow_async(user_goal, conversation_history="", client=None, staged=True):
    """Async generator streaming events from local agent loop."""
    import asyncio
    active_history = f"{SYSTEM_PROMPT}\n{conversation_history}\nUser Goal: {user_goal}\n"
    final_answer = "No final answer was reached."
    recent_fingerprints = []
    staged_files = []

    for step in range(1, MAX_STEPS + 1):
        yield {"type": "step_start", "step": step}
        response = await asyncio.to_thread(query_ollama, active_history)
        if not response.strip():
            yield {"type": "empty_response", "step": step}
            break

        active_history += response + "\n"

        if "Final Answer:" in response:
            match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL)
            final_answer = match.group(1).strip() if match else response
            yield {"type": "final", "final_answer": final_answer, "step": step}
            break

        tool_name, args, content, old, new, parse_error = parse_response(response)
        if parse_error:
            obs = f"Error: {parse_error}"
            yield {"type": "parse_error", "error": parse_error, "step": step}
        elif tool_name not in TOOLS and tool_name not in ("write_file", "edit_file", "read_file"):
            obs = f"Error: Tool '{tool_name}' does not exist."
            yield {"type": "unknown_tool", "tool": tool_name, "step": step}
        else:
            fingerprint = json.dumps({"tool": tool_name, "args": args, "content": content, "old": old}, sort_keys=True, default=str)
            recent_fingerprints.append(fingerprint)
            if len(recent_fingerprints) > STUCK_REPEAT_LIMIT:
                recent_fingerprints.pop(0)
            if len(recent_fingerprints) == STUCK_REPEAT_LIMIT and len(set(recent_fingerprints)) == 1:
                final_answer = "Task aborted: agent got stuck repeating the same action."
                yield {"type": "aborted", "reason": "stuck_loop"}
                break

            yield {"type": "tool_call", "tool": tool_name, "args": args, "step": step}
            try:
                if tool_name == "read_file":
                    fn = args.get("filename") or args.get("path") or ""
                    obs = read_file(filename=fn, staging=staged)
                elif tool_name == "write_file":
                    fn = args.get("filename") or args.get("path") or ""
                    obs = write_file(filename=fn, content=content, task_description=user_goal, staging=staged)
                    if fn not in staged_files:
                        staged_files.append(fn)
                elif tool_name == "edit_file":
                    fn = args.get("filename") or args.get("path") or ""
                    obs = edit_file(filename=fn, old=old, new=new, task_description=user_goal, staging=staged)
                    if fn not in staged_files:
                        staged_files.append(fn)
                else:
                    obs = TOOLS[tool_name](**args) if isinstance(args, dict) else TOOLS[tool_name](args)
            except Exception as e:
                obs = f"Error executing tool: {str(e)}"

            yield {"type": "observation", "observation": obs[:1000], "step": step}

        if len(obs) > MAX_TOOL_OUTPUT_CHARS:
            obs = obs[:MAX_TOOL_OUTPUT_CHARS] + "\n...[TRUNCATED]..."
        active_history += f"Observation: {obs}\n"

    yield {
        "type": "completed",
        "status": "completed" if "Final Answer:" in active_history else "failed",
        "final_answer": final_answer,
        "staged_files": staged_files
    }


async def run_agentic_workflow_async(user_goal, conversation_history="", client=None, staged=True):
    """Executes the async local workflow and returns consolidated dictionary."""
    log = []
    final_res = {"status": "failed", "final_answer": "No answer reached", "staged_files": []}
    async for event in stream_agentic_workflow_async(user_goal, conversation_history, client, staged=staged):
        log.append(event)
        if event.get("type") == "completed":
            final_res = {
                "status": event.get("status", "completed"),
                "final_answer": event.get("final_answer", ""),
                "staged_files": event.get("staged_files", []),
            }
        elif event.get("type") == "final":
            final_res["final_answer"] = event.get("final_answer", "")
            final_res["status"] = "completed"

    final_res["execution_log"] = log
    return final_res


def main():
    if "--serve" in sys.argv or "-s" in sys.argv:
        import uvicorn
        print("🌐 Starting JARVIS Local Agent Bridge Server on port 8008...")
        uvicorn.run("bridge_server:app", host="0.0.0.0", port=8008, reload=False)
        return

    print("🤖 JARVIS Local Agent Online (Pro). Type 'exit' or 'quit' to close.")
    print(f"📂 Workspace: {WORKSPACE_DIR}\n")

    conversation_history = ""
    while True:
        try:
            user_goal = input("\nJARVIS > ")
            if user_goal.strip().lower() in ["exit", "quit"]:
                break
            if not user_goal.strip():
                continue

            res = run_agentic_workflow(user_goal, conversation_history, staging=True)
            print(f"\nFinal Answer: {res['final_answer']}")
            conversation_history += f"\nUser Goal: {user_goal}\nFinal Answer: {res['final_answer']}\n"
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
