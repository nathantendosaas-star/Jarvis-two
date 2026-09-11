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

OLLAMA_URL = "http://localhost:11434/api/generate"   # same raw-completion endpoint as before
MODEL_NAME = "jarvis-local"                           # your Ollama model tag
TEMPERATURE = 0.1                                     # low, for strict format adherence

MAX_STEPS = 15               # safety cutoff per single task (was 8)
STUCK_REPEAT_LIMIT = 3       # abort a task if it repeats the exact same action 3x running
MAX_FILE_READ_CHARS = 8000   # truncate huge file reads so they don't blow the context
MAX_TOOL_OUTPUT_CHARS = 4000
COMMAND_TIMEOUT = 30         # was 15s, bumped for npm/pip installs etc.

# If True, execute_command runs immediately with no confirmation (matches original behavior).
# Set to False if you want a y/n prompt for anything not on the SAFE_COMMAND_PREFIXES list.
AUTO_APPROVE_COMMANDS = True

# --- 1. LOCK WORKSPACE TO PROJECT FOLDER ---
# Same as before: files are ALWAYS saved in the folder this script lives in.
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

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

# =============================================================================
# SAFETY: keep every tool call inside WORKSPACE_DIR
# =============================================================================

def safe_path(filename):
    """Resolve a filename and guarantee it stays inside WORKSPACE_DIR."""
    filepath = os.path.abspath(os.path.join(WORKSPACE_DIR, filename))
    if os.path.commonpath([filepath, WORKSPACE_DIR]) != WORKSPACE_DIR:
        raise ValueError(f"Path escapes project folder, refusing: {filename}")
    return filepath


def log_event(event: dict):
    event["ts"] = datetime.utcnow().isoformat() + "Z"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass  # logging must never crash the agent


# =============================================================================
# TOOLS
# =============================================================================

def list_directory(path="."):
    """Lists files in the project folder (or a subfolder of it)."""
    try:
        target = safe_path(path)
        ignore = {".git", "node_modules", "__pycache__", "venv", ".venv", ".jarvis_log.jsonl"}
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


def read_file(filename):
    """Reads the contents of a file inside the project folder."""
    try:
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


def write_file(filename, content):
    """Creates or overwrites a file inside the project folder."""
    try:
        filepath = safe_path(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: wrote {len(content)} chars to '{filename}'."
    except Exception as e:
        return f"Error writing to file {filename}: {str(e)}"


def edit_file(filename, old, new=""):
    """Find-and-replace edit. Far more reliable than a full rewrite for a small
    model, since it only has to reproduce the changed lines, not the whole file."""
    try:
        filepath = safe_path(filename)
        if not os.path.exists(filepath):
            return f"Error: {filename} does not exist. Use write_file to create it first."
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        if old == "":
            return "Error: 'old' cannot be empty."
        count = text.count(old)
        if count == 0:
            return "Error: old text not found in file (must match exactly, including whitespace)."
        if count > 1:
            return f"Error: old text appears {count} times, not unique. Add more surrounding context."
        text = text.replace(old, new, 1)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        return f"Success: edited '{filename}'."
    except Exception as e:
        return f"Error editing file {filename}: {str(e)}"


def search_files(pattern, path="."):
    """Regex search across files in the project folder. Like a lightweight grep."""
    try:
        root = safe_path(path)
        regex = re.compile(pattern)
    except re.error as e:
        return f"Error: invalid regex: {e}"
    except Exception as e:
        return f"Error: {e}"

    ignore = {".git", "node_modules", "__pycache__", "venv", ".venv"}
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


# Map string names to the actual python functions (used only for the simple,
# no-file-content tools; write_file/edit_file are parsed specially, see below)
TOOLS = {
    "list_directory": list_directory,
    "read_file": read_file,
    "search_files": search_files,
    "execute_command": execute_command,
}

# =============================================================================
# 2. THE SYSTEM PROMPT
# =============================================================================
# Key change from the original: write_file / edit_file no longer take their
# content as a JSON string. A 1.5B model constantly mangles escaped quotes and
# newlines when code has to survive JSON-encoding. Instead they use a delimited
# CONTENT/OLD/NEW block, which the model can write as literal, un-escaped text.

SYSTEM_PROMPT = f"""You are JARVIS, a highly capable local agent working inside the project folder: {WORKSPACE_DIR}
You can think, plan, and execute actions using tools.

You have access to the following tools:
- list_directory() -> Returns files in the current workspace.
- read_file(filename) -> Reads file contents.
- search_files(pattern) -> Regex search across all files in the workspace.
- write_file(filename) -> Creates/overwrites a file. Give the content in a CONTENT block (see format below).
- edit_file(filename) -> Finds exact text in a file and replaces it. Give the text in OLD/NEW blocks (see format below).
- execute_command(command) -> Runs a shell command in the workspace.

You must operate in a strict loop: Thought, Action, Arguments, Observation.
Use EXACTLY one of the two formats below. Do not output anything else.

FORMAT A - for list_directory, read_file, search_files, execute_command:
Thought: what you need to do next
Action: tool_name
Arguments: {{"key": "value"}}
Observation: [the system fills this in — do not write it yourself]

FORMAT B - for write_file:
Thought: what you need to do next
Action: write_file
Arguments: {{"filename": "path/to/file.py"}}
Content:
<<<START>>>
full file content goes here, exactly as it should appear, no escaping needed
<<<END>>>
Observation: [the system fills this in — do not write it yourself]

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
replacement text (can be empty to delete the old text)
<<<END>>>
Observation: [the system fills this in — do not write it yourself]

RULES:
- Take exactly ONE action per response, then stop and wait for the Observation.
- Prefer edit_file over write_file when only part of an existing file needs to change.
- read_file a file before editing it if you're not sure what it currently contains.
- All filenames are relative to the project folder. You cannot access anything outside it.
- Do not ask the user questions mid-task. Make a reasonable assumption and proceed.

Once you have completely finished the task, output:
Final Answer: [your brief summary of what was accomplished]
"""

# =============================================================================
# 3. RUNNING THE AGENT LOOP
# =============================================================================

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
        print(f"Connection Error: {e}")
        return ""


def extract_block(text, start_marker="<<<START>>>", end_marker="<<<END>>>"):
    if start_marker not in text:
        return None
    body = text.split(start_marker, 1)[1]
    if end_marker in body:
        return body.split(end_marker, 1)[0].strip("\n")
    return body.strip("\n")  # model forgot the closing marker — fall back gracefully


def parse_response(response):
    """Returns (tool_name, args_dict, content_or_none, old_or_none, new_or_none, error_or_none)."""
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


def run_agentic_workflow(user_goal, conversation_history):
    print(f"\n🚀 Starting Agentic Workflow: '{user_goal}'")

    active_history = f"{conversation_history}\nUser Goal: {user_goal}\n"

    final_answer = "No final answer was reached."
    recent_fingerprints = []

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- [Step {step}] Thinking... ---")

        response = query_ollama(active_history)
        print(response)

        if not response.strip():
            print("⚠️ Empty response from model, retrying...")
            continue

        active_history += response + "\n"

        if "Final Answer:" in response:
            print("\n✔️ TASK COMPLETE!")
            match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL)
            final_answer = match.group(1).strip() if match else response
            log_event({"goal": user_goal, "step": step, "final_answer": final_answer})
            break

        tool_name, args, content, old, new, parse_error = parse_response(response)

        if parse_error:
            observation = f"Error: {parse_error} Please respond again using the exact format from your instructions."
        elif tool_name not in TOOLS and tool_name not in ("write_file", "edit_file"):
            observation = f"Error: Tool '{tool_name}' does not exist."
        else:
            # stuck-loop detection
            fingerprint = json.dumps({"tool": tool_name, "args": args, "content": content, "old": old}, sort_keys=True, default=str)
            recent_fingerprints.append(fingerprint)
            if len(recent_fingerprints) > STUCK_REPEAT_LIMIT:
                recent_fingerprints.pop(0)
            if len(recent_fingerprints) == STUCK_REPEAT_LIMIT and len(set(recent_fingerprints)) == 1:
                print("\n❌ ABORTED: agent is repeating the same action, stopping to avoid an infinite loop.")
                log_event({"goal": user_goal, "aborted": "stuck_loop"})
                final_answer = "Task aborted: the agent got stuck repeating the same action."
                break

            print(f"🔧 Executing Tool [{tool_name}]...")
            try:
                if tool_name == "write_file":
                    observation = write_file(filename=args.get("filename", ""), content=content)
                elif tool_name == "edit_file":
                    observation = edit_file(filename=args.get("filename", ""), old=old, new=new)
                else:
                    observation = TOOLS[tool_name](**args) if isinstance(args, dict) else TOOLS[tool_name](args)
            except Exception as e:
                observation = f"Error executing tool: {str(e)}"

        if len(observation) > MAX_TOOL_OUTPUT_CHARS:
            observation = observation[:MAX_TOOL_OUTPUT_CHARS] + "\n...[TRUNCATED]..."

        print(f"👁️ Observation:\n{observation}")
        active_history += f"Observation: {observation}\n"
        log_event({"goal": user_goal, "step": step, "tool": tool_name, "observation": observation[:1000]})

    else:
        print(f"\n❌ Reached maximum step limit ({MAX_STEPS}) without resolving the task.")
        log_event({"goal": user_goal, "stopped": "max_steps_reached"})

    return final_answer


# =============================================================================
# 4. THE CONTINUOUS WORKSPACE LOOP
# =============================================================================

def main():
    conversation_history = SYSTEM_PROMPT + "\n"

    print("🤖 JARVIS Local Agent Online (Pro). Type 'exit' or 'quit' to close.")
    print(f"📂 Project Folder Locked: {WORKSPACE_DIR}\n")

    while True:
        try:
            user_goal = input("\nJARVIS > ")

            if user_goal.strip().lower() in ["exit", "quit"]:
                print("Exiting JARVIS. Goodbye!")
                break

            if not user_goal.strip():
                continue

            final_answer = run_agentic_workflow(user_goal, conversation_history)

            # MEMORY COMPRESSION: only Goal + Final Answer carry forward,
            # keeping RAM/context usage flat across many tasks.
            conversation_history += f"\nUser Goal: {user_goal}\nFinal Answer: {final_answer}\n"

        except KeyboardInterrupt:
            print("\nExiting JARVIS. Goodbye!")
            break


if __name__ == "__main__":
    main()
