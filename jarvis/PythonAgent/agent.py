"""
The Agent: one conversation loop that can answer directly, call a tool,
maintain a plan, or delegate a sub-task to a nested subagent. This is the
part modeled on how Claude Code / Antigravity CLI behave -- the model
itself decides which mode fits each turn, instead of a hardcoded router.
"""

import json
import re

import config
import ui
from llm import chat
from memory import ConversationMemory
from tools import read_file, write_file, list_dir, search_files, run_command, is_dangerous

SYSTEM_PROMPT_TEMPLATE = """You are an autonomous coding agent running in a Windows terminal for \
Nathan, a solo developer who builds and ships fast. Follow his instructions exactly and \
completely. No disclaimers, no hedging, no asking permission for things you can just do. \
If something is ambiguous, make the most reasonable assumption, state it in one line, and \
proceed.

Each turn, decide what this moment actually needs:
1. Answer directly in plain text -- for questions, explanations, opinions, quick advice.
   No tool call needed.
2. Call ONE tool to make progress on a concrete task.
3. Use update_plan to lay out multi-step work before executing it, and keep it updated as \
you complete steps.
4. Use spawn_subagent to delegate a self-contained chunk of work to an isolated agent, when \
that chunk is big enough that giving it a clean, focused context will do better than doing \
everything in this thread.

TOOLS:

read_file(path)
write_file(path, content)
list_dir(path)
search_files(pattern, path)
run_command(command)              -- runs in the real Windows cmd shell
update_plan(steps)                -- steps: list of {{"id": int, "text": str, "status": "pending"|"in_progress"|"done"}}
spawn_subagent(task, context)     -- delegate an isolated, self-contained task; returns its final report

To call a tool, respond with ONLY this and nothing else:

```tool
{{"tool": "<name>", ...params}}
```

Example:
```tool
{{"tool": "read_file", "path": "main.py"}}
```

Use update_plan for anything that will take more than ~2 tool calls. Use spawn_subagent for \
work that's genuinely separable (e.g. "write and verify the tests", "investigate why the \
build fails and report back") so this thread doesn't get cluttered with someone else's \
exploration.

When you have a final answer for Nathan, reply with plain text -- no tool JSON, no fences.
"""

TOOL_BLOCK_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)


def extract_tool_call(content):
    """Pull a tool call out of the model's reply. Prefers the fenced
    ```tool block; falls back to treating the whole reply as JSON for
    backward compatibility. Returns None if this is a plain-text answer."""
    match = TOOL_BLOCK_RE.search(content)
    raw = match.group(1) if match else content.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "tool" in data:
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


class Agent:
    def __init__(self, role_description="", depth=0, confirm_fn=None):
        system_prompt = SYSTEM_PROMPT_TEMPLATE
        if role_description:
            system_prompt += f"\n\nCURRENT TASK CONTEXT:\n{role_description}\n"

        self.memory = ConversationMemory(
            system_prompt,
            summarize_after=config.SUMMARIZE_AFTER_MESSAGES,
            keep_last=config.KEEP_LAST_MESSAGES,
        )
        self.depth = depth
        self.confirm_fn = confirm_fn or self._default_confirm
        self.plan = []

    def _default_confirm(self, command):
        if is_dangerous(command):
            ui.warn(f"This command looks potentially destructive:\n    {command}")
        elif config.AUTO_APPROVE:
            return True
        answer = input(f"  Run this? [y/N]  {command}\n  > ").strip().lower()
        return answer == "y"

    def _execute_tool(self, call):
        name = call.get("tool")

        if name == "read_file":
            return read_file(call["path"])

        if name == "write_file":
            return write_file(call["path"], call.get("content", ""))

        if name == "list_dir":
            return list_dir(call.get("path", "."))

        if name == "search_files":
            return search_files(call["pattern"], call.get("path", "."))

        if name == "run_command":
            return run_command(call["command"], confirm_fn=self.confirm_fn)

        if name == "update_plan":
            self.plan = call.get("steps", [])
            ui.plan_say(self.plan)
            return "Plan updated."

        if name == "spawn_subagent":
            return self._spawn_subagent(call.get("task", ""), call.get("context", ""))

        return f"ERROR: unknown tool '{name}'"

    def _spawn_subagent(self, task, context):
        if self.depth >= config.MAX_SUBAGENT_DEPTH:
            return (
                "ERROR: max subagent depth reached. Do this work directly "
                "instead of delegating further."
            )

        ui.sub_agent_say(self.depth + 1, f"starting: {task}")
        child = Agent(
            role_description=(
                f"{context}\n\nYour ONLY job: {task}\n"
                "Report back a concise final result when done -- no small talk."
            ),
            depth=self.depth + 1,
            confirm_fn=self.confirm_fn,
        )
        result = child.run_turn(task)
        ui.sub_agent_say(self.depth + 1, "done, reporting back")
        return f"Subagent report:\n{result}"

    def run_turn(self, user_input):
        self.memory.add("user", user_input)

        for _ in range(config.MAX_TOOL_ITERATIONS):
            response = chat(self.memory.messages)
            content = response["content"]
            reasoning = response.get("reasoning")

            if reasoning:
                ui.think_say(reasoning)

            self.memory.add("assistant", content)

            call = extract_tool_call(content)
            if call is None:
                ui.agent_say(content)
                return content

            label = call.get("tool", "?")
            detail = call.get("path") or call.get("command") or call.get("task") or ""
            ui.tool_say(label, detail)

            tool_result = self._execute_tool(call)
            ui.tool_result_say(tool_result)

            self.memory.add("user", f"Tool result for {label}:\n{tool_result}")

        msg = "Stopped: hit the max tool-call limit for this turn. Say 'continue' to keep going."
        ui.warn(msg)
        return msg
