# Agent CLI

An autonomous coding agent for your terminal, running DeepSeek V4 Flash via
OpenRouter. Modeled on how Claude Code / Antigravity CLI behave: the model
itself decides, turn by turn, whether to answer directly, call a tool, plan
multi-step work, or delegate a chunk of work to a subagent.

## First: rotate your API key

The key that was in the old script is now burned -- it was pasted in
plaintext into a file. Go rotate it on openrouter.ai before doing anything
else. This version never has a key in code; it only reads from the
environment or a local `.env` file that's gitignored.

## Setup

```
cd agent_cli
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` and paste your key in place of `your-key-here`. Or, if you'd
rather not use a file, set it directly in cmd:

```
setx OPENROUTER_API_KEY "your-key-here"
```

(`setx` persists across sessions but needs a fresh cmd window to take
effect. Use `set OPENROUTER_API_KEY=...` instead for a one-off session.)

## Run

```
python main.py
```

Type naturally. `exit` to quit, `/plan` to see the current plan, `/auto` to
toggle auto-approving safe-looking commands.

## How it decides what to do

There's no separate "classifier" step burning extra API calls -- the
routing logic lives in the system prompt (`agent.py`), and the model picks
per turn:

- **Plain text reply** -- questions, explanations, opinions. No tool call.
- **One tool call** -- `read_file`, `write_file`, `list_dir`,
  `search_files`, `run_command`.
- **`update_plan`** -- for anything that's more than ~2 tool calls, the
  model lays out numbered steps with status (`pending` / `in_progress` /
  `done`), printed to your terminal and kept current as it works. This is
  the same idea as Claude Code's todo list or Antigravity's task tracking
  -- you can always see what it thinks it's doing.
- **`spawn_subagent`** -- delegates a self-contained chunk of work (e.g.
  "write tests and verify they pass") to a fresh, isolated agent with its
  own conversation. It runs to completion and reports back a summary, so
  its exploration doesn't clutter the main thread. Capped at 2 levels deep
  by default (`AGENT_MAX_SUBAGENT_DEPTH` in `.env`) so it can't spiral.

Tool calls use a fenced block so parsing survives the model adding stray
text around it:

````
```tool
{"tool": "read_file", "path": "main.py"}
```
````

## Safety model

`run_command` actually executes in your real cmd shell, so:

- Read-only-looking commands (`dir`, `git status`, `type`, etc.) run
  without asking.
- Everything else asks for a `y/N` confirmation before running -- unless
  you've toggled `/auto` on (or set `AGENT_AUTO_APPROVE=true` in `.env`).
- A fixed list of destructive patterns (`rm -rf`, `format`, `diskpart`,
  force-push, fork bombs, etc.) **always** shows a warning and asks for
  confirmation, even in auto-approve mode. This list is in `tools.py` --
  add to it if you think of others.

## Memory

Long sessions get summarized automatically once the message count crosses
a threshold (`memory.py`), so you don't blow the context window or run up
a huge bill on a long build session. The summary keeps file names, paths,
decisions, and stated objectives; the last few messages stay verbatim.

## Files

```
main.py      entry point / REPL
agent.py     the Agent class -- decision loop, tool dispatch, subagents
tools.py     read_file / write_file / list_dir / search_files / run_command
memory.py    rolling conversation summarization
llm.py       the one place that talks to OpenRouter
ui.py        colored terminal output
config.py    all settings, read from env / .env -- no secrets in code
```

## Extending it

To add a tool: implement it in `tools.py`, add a branch in
`Agent._execute_tool`, and describe it in `SYSTEM_PROMPT_TEMPLATE` in
`agent.py` so the model knows it exists. Same pattern the original script
used, just with a name and description so the model can actually decide
when to reach for it.

## What's different from the old version

- API key is no longer in the source file.
- Tool-call parsing survives the model adding text around the JSON
  (`json.loads` on the whole message would previously break constantly).
- Commands are gated by a confirm step instead of running blind.
- Actual planning (`update_plan`) and delegation (`spawn_subagent`) exist
  now -- the old version was a single flat loop with no way to structure
  bigger tasks or split work off into an isolated context.
- Memory summarization no longer discards the trigger message and no
  longer replaces the *entire* history with just the summary -- it keeps
  the last few messages verbatim alongside it, which is closer to how
  actual agentic tools do rolling context.
