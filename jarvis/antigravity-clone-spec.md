# Cloning Antigravity 2.0 — Agentic Core: Full Technical Spec

Scope: this covers the **agentic engine** (subagent delegation, permissions, sandboxing, lifecycle, tool routing). It does not cover the IDE/CLI/UI chrome — those are just front-ends bolted onto this engine. Build the engine first; it's UI-agnostic by design (that's literally why Antigravity ships as IDE + CLI + SDK + Hub off one core).

---

## 0. System shape

```
┌─────────────────────────────────────────────┐
│  Surface (CLI / IDE panel / SDK caller)      │  ← thin client, sends prompts, renders state
└───────────────────┬───────────────────────────┘
                     │
┌────────────────────▼───────────────────────┐
│  Orchestration Engine (the part to build)   │
│  ┌────────────┐  ┌────────────┐            │
│  │ Agent       │  │ Permission │            │
│  │ Registry    │  │ Engine     │            │
│  └────────────┘  └────────────┘            │
│  ┌────────────┐  ┌────────────┐            │
│  │ Execution   │  │ Message    │            │
│  │ Loop        │  │ Bus        │            │
│  └────────────┘  └────────────┘            │
│  ┌────────────┐  ┌────────────┐            │
│  │ Sandbox/    │  │ Workspace  │            │
│  │ Process Mgr │  │ Manager    │            │
│  └────────────┘  └────────────┘            │
└───────────────────┬───────────────────────────┘
                     │
        Tool calls (MCP servers, shell, filesystem, browser)
```

Six components. Build in roughly this order: Agent Registry → Execution Loop → Message Bus → Permission Engine → Workspace Manager → Sandbox/Process Manager. Each is independently testable.

---

## 1. Agent Registry

**Job:** load agent definitions from disk, validate them, expose them to the planner.

### File format
`.md` with YAML frontmatter, one file per agent.

```yaml
---
name: code-auditor              # required, unique, [a-z0-9-]+
description: >                  # required — this is what the ROUTER reads to decide delegation
  Use for security audits, static analysis, dependency vuln scanning.
tools:                          # required, explicit allowlist — no wildcard by default
  - view_file
  - grep_search
  - run_command
model: pro                      # inherit | flash | pro
mainAgent: false                # can a human select this as top-level chat agent?
subagent: true                  # can invoke_subagent() spawn this?
commandExecutionPolicy: sandbox # off | auto | eager | sandbox
mcpServers: []                  # custom MCP servers scoped to this agent only
skills: []                      # paths to skill files, injected into system prompt
plugins: []
---

# System Prompt
You are an expert security auditor...

# Guidelines
1. Read-only unless explicitly told to modify.
2. Flag injection risk, hardcoded secrets, unvalidated input.
```

### Discovery
On boot, scan (in priority order, later overrides earlier on name collision):
1. `plugins/*/agents/*.md` (bundled)
2. `~/.config/yourapp/agents/*.md` (global, machine-wide)
3. `.agents/agents/*.md` (per-repo, highest priority)

### Validation — do this at LOAD time, not spawn time
This is the #1 lesson from Antigravity's actual bug: they validate tool names lazily, at invocation, and a typo'd tool name **hangs the subagent silently** instead of failing. Don't repeat this.

```python
class AgentDef(BaseModel):
    name: str
    description: str
    tools: list[str] = []
    model: Literal["inherit", "flash", "pro"] = "inherit"
    mainAgent: bool = True
    subagent: bool = True
    commandExecutionPolicy: Literal["off","auto","eager","sandbox"] = "sandbox"
    mcpServers: list[dict] = []
    skills: list[str] = []
    plugins: list[str] = []
    system_prompt: str  # parsed from markdown body

def load_agent(path: Path, tool_registry: ToolRegistry) -> AgentDef:
    fm, body = split_frontmatter(path.read_text())
    agent = AgentDef(**fm, system_prompt=body)
    unknown = set(agent.tools) - tool_registry.known_names()
    if unknown:
        raise AgentLoadError(f"{path}: unknown tools {unknown}")  # FAIL LOUD, AT LOAD
    return agent
```

Registry is just `dict[str, AgentDef]` in memory, rebuilt on file change (watch the agent dirs with a filesystem watcher, hot-reload — cheap and saves you restarting your whole session every time you tweak a subagent).

---

## 2. Execution Loop (the actual "agent")

Every agent instance — parent or child — runs the **same loop**. There's no special-cased "orchestrator" class; the parent is just an agent whose toolset happens to include `invoke_subagent`.

```python
class AgentInstance:
    id: str                      # unique conversation id
    definition: AgentDef
    state: Literal["running","idle","killed"]
    messages: list[Message]      # THIS agent's own context — never shared
    parent_id: str | None
    children: list[str]          # child agent ids
    workspace: WorkspaceHandle
    depth: int                   # nesting depth from root

    async def run_turn(self, incoming: Message | None):
        self.state = "running"
        if incoming:
            self.messages.append(incoming)
        while True:
            response = await model_call(
                model=resolve_model(self.definition.model),
                system=self.definition.system_prompt,
                messages=self.messages,
                tools=resolve_tools(self.definition.tools),
            )
            self.messages.append(response)
            if response.tool_calls:
                for call in response.tool_calls:
                    result = await dispatch_tool(self, call)  # permission check happens IN HERE
                    self.messages.append(result)
                continue  # loop again with tool results in context
            else:
                break  # model produced a final text response, turn ends
        self.state = "idle"
        if self.parent_id:
            await message_bus.send(to=self.parent_id, from_=self.id,
                                    content=synthesize_result(self.messages))
```

Key property: **context never crosses the parent/child boundary except through explicit messages.** The child's `self.messages` starts empty at spawn — this is what gives you the "clean slate" behavior and is also what prevents context-window blowup as your agent tree grows. This is the single most important design decision in the whole system; get it right before anything else.

---

## 3. `invoke_subagent` — the delegation tool itself

This is just another tool in the parent's toolset, dispatched like any other, but it has special side effects: it creates a new `AgentInstance`.

```python
async def invoke_subagent(
    caller: AgentInstance,
    role: str,                 # name in Agent Registry
    prompt: str,
    workspace_mode: Literal["inherit","branch","share"] = "inherit",
    model_override: str | None = None,
) -> str:  # returns child_id immediately, does NOT block
    if caller.depth + 1 > MAX_NESTING_DEPTH:      # 10, hard-coded constant
        raise NestingLimitExceeded()

    agent_def = registry.get(role)
    if not agent_def.subagent:
        raise PermissionError(f"{role} is not invocable as a subagent")

    workspace = workspace_manager.provision(
        parent_workspace=caller.workspace,
        mode=workspace_mode,
    )

    child = AgentInstance(
        id=new_id(),
        definition=agent_def,
        state="running",
        messages=[],                     # <-- fresh, no parent history
        parent_id=caller.id,
        children=[],
        workspace=workspace,
        depth=caller.depth + 1,
    )
    child.permissions = intersect_permissions(caller.permissions, agent_def)  # see §4

    registry_of_instances[child.id] = child
    caller.children.append(child.id)

    asyncio.create_task(child.run_turn(Message(role="user", content=prompt)))  # fire and forget — concurrency
    return child.id
```

**This must be non-blocking.** The parent's loop continues immediately after spawning — it can spawn 5 more children, or keep working itself, while the first one runs. This is what "concurrent subagents" actually means at the code level: `asyncio.create_task` (or your language's equivalent), not a blocking function call.

Workspace modes, concretely:

| Mode | Implementation |
|---|---|
| `inherit` | child gets the same absolute path as parent, no copy, no isolation |
| `branch` | `git worktree add <tmpdir> -b agent/<child_id>` off parent's current branch; child operates entirely inside `<tmpdir>` |
| `share` | child gets its own execution context/process, but filesystem path is the same directory as parent (writes are visible to both, no worktree) |

`branch` is where most of your engineering effort goes if you want concurrent writers to be safe. Without it, two subagents editing files in the same directory will race and corrupt each other's diffs — this is the actual failure mode that motivates the whole workspace-mode concept.

---

## 4. Permission Engine

Two layers: **static config** (allow/deny/ask lists) and **runtime inheritance** (parent → child).

### 4a. Config format
```yaml
# .agents/permissions.yaml (per-project) or ~/.config/yourapp/permissions.yaml (global)
allow:
  - command(git)                          # exact prefix match
  - command(npm run (build|lint|test))    # regex
  - unsandboxed(git push)                 # allow this OUTSIDE the sandbox specifically
  - read_url(docs.python.org)
deny:
  - command(rm -rf)
  - command(curl.*\|.*sh)                 # block curl-pipe-to-shell, obviously
ask:
  - "*"                                   # default fallback for anything unmatched
```

Resolution order for any action: **deny > allow > ask (default)**. Deny always wins even if an allow rule would also match — check deny first, always.

```python
def resolve_permission(action: str, config: PermissionConfig) -> Literal["allow","deny","ask"]:
    if any(re.fullmatch(pat, action) for pat in config.deny):
        return "deny"
    if any(re.fullmatch(pat, action) for pat in config.allow):
        return "allow"
    return "ask"
```

Defaults if nothing configured (copy these exactly, they're sane):
- File read/write **inside** the active project/workspace directory → auto-allow
- File access **outside** the workspace → ask
- `read_url` / `execute_url` (browser actions) → ask
- Shell commands → ask, unless `commandExecutionPolicy: auto` on the agent def
- MCP tool calls → ask, unless explicitly allow-listed

### 4b. Runtime inheritance (parent → child)
This is the rule that actually matters for safety: **a child's effective permission set is the intersection, never the union, of its own config and its parent's current permission set.**

```python
def intersect_permissions(parent: PermissionSet, child_def: AgentDef) -> PermissionSet:
    # child can only ever be as permissive as its parent, regardless of what
    # the child's own agent definition claims
    return PermissionSet(
        allow=parent.allow & agent_declared_allow(child_def),
        deny=parent.deny | agent_declared_deny(child_def),   # deny is a union — more restrictive wins
        command_execution=min(parent.command_execution, child_def.commandExecutionPolicy,
                               key=policy_strictness_rank),
        sandbox_enabled=parent.sandbox_enabled or child_def.commandExecutionPolicy == "sandbox",
    )
```

If a subagent hits an `ask` action mid-execution, it does **not** prompt its own hidden UI — the request bubbles to whatever surface owns the root of the tree (the human-facing terminal/panel). Implement this as: child publishes a `permission_request` event onto the message bus tagged with the root agent id; execution of that specific tool call blocks (just that call, not the whole event loop) until a response event arrives.

---

## 5. Sandbox / Process Manager

This is the part people skip and regret. Two levels of containment, build the first one first:

**Level 1 — process-level restriction (do this first, it's ~80% of the value for ~10% of the effort):**
- Spawn shell commands via `subprocess` with a scrubbed environment (strip `AWS_*`, `*_TOKEN`, `*_KEY`, etc. unless explicitly allow-listed)
- Restrict `cwd` to the workspace path, refuse commands with `..` path traversal outside it
- Strip network env vars / set `http_proxy` to a blackhole address if `sandbox_network_access: false`

**Level 2 — kernel-level isolation (do this when you actually trust agents to run unattended):**
- Linux: run commands inside a `bubblewrap` (`bwrap`) or `firejail` namespace — restricted filesystem view, no network namespace if network is denied, no access to host devices
- This is what Antigravity means by "kernel-level isolation... commands run in a restricted environment with limited file system and network access." Don't try to build this yourself with raw `chroot` — use an existing sandboxing tool, it's a solved problem and getting it wrong is a real security bug, not a cosmetic one.

Sandbox toggle should be a **agent-def field** (`commandExecutionPolicy: sandbox`) AND a **global override** (settings.json), with global-strict always winning:

```python
def effective_sandbox(agent_policy: str, global_strict_mode: bool) -> bool:
    if global_strict_mode:
        return True  # strict mode forces sandbox + denies network, no exceptions
    return agent_policy == "sandbox"
```

---

## 6. Lifecycle State Machine

```
                 ┌──────────┐
   spawn ───────▶│ RUNNING  │◀────────┐
                 └────┬─────┘         │ message received
                      │ turn ends,    │ (auto-wake)
                      │ result sent   │
                      ▼               │
                 ┌──────────┐         │
                 │  IDLE    │─────────┘
                 └────┬─────┘
                      │ kill()
                      ▼
                 ┌──────────┐
                 │ KILLED   │  (terminal — cleanup worktree, keep transcript)
                 └──────────┘
```

Implementation:
```python
class AgentInstance:
    async def receive(self, msg: Message):
        if self.state == "killed":
            raise DeadAgentError()
        if self.state == "idle":
            await self.run_turn(msg)   # auto-wake, KEEP self.messages — don't reset
        elif self.state == "running":
            self.pending_inbox.append(msg)  # queue it, deliver after current turn

    def kill(self):
        self.state = "killed"
        workspace_manager.cleanup(self.workspace)   # `git worktree remove`, delete tmpdir
        transcript_store.flush(self.id, self.messages)  # keep JSONL on disk regardless
```

Store every agent's full message history as JSONL on disk continuously (append per turn, not just at kill) — `~/.yourapp/transcripts/<agent_id>.jsonl`. This is your audit trail and also your debugging tool when a subagent does something weird; don't make it kill-triggered only, or a crash loses the log.

---

## 7. Message Bus / Inter-agent communication

Minimal viable version: an in-process pub/sub keyed by agent id, since v1 is single-machine.

```python
class MessageBus:
    def __init__(self):
        self.instances: dict[str, AgentInstance] = {}

    async def send(self, to: str, from_: str, content: str):
        target = self.instances[to]
        await target.receive(Message(role="user", content=content, meta={"from": from_}))
```

MVP routing rules — don't build general any-to-any yet:
- child → parent: automatic, on turn completion (`synthesize_result`)
- parent → child: explicit, via a `send_to_subagent(child_id, message)` tool exposed to the parent
- peer → peer: skip entirely until you have a concrete case that needs it

`synthesize_result` — don't just dump the child's full message list back to the parent, that defeats the whole point of context isolation. Do a final model call within the child asking it to summarize its own work into a short result:

```python
async def synthesize_result(messages: list[Message]) -> str:
    return await model_call(
        model="flash",  # cheap model, this is just summarization
        system="Summarize the outcome of this task in 3-5 sentences for your supervisor. Include any files changed and any blockers.",
        messages=messages,
    )
```

---

## 8. Nesting & resource guards

```python
MAX_NESTING_DEPTH = 10
MAX_CONCURRENT_CHILDREN_PER_PARENT = 8   # pick a number, Antigravity doesn't publish theirs but cap it
MAX_TOTAL_LIVE_AGENTS = 50               # global circuit breaker

def check_spawn_allowed(caller, registry_of_instances):
    if caller.depth + 1 > MAX_NESTING_DEPTH:
        raise NestingLimitExceeded()
    if len(caller.children) >= MAX_CONCURRENT_CHILDREN_PER_PARENT:
        raise TooManyChildren()
    live = sum(1 for a in registry_of_instances.values() if a.state != "killed")
    if live >= MAX_TOTAL_LIVE_AGENTS:
        raise GlobalAgentLimitExceeded()
```

Enforce all three at spawn time, not after the fact. A mis-prompted planner recursively spawning itself is the actual failure mode this guards against — it will happen, budget for it.

---

## 9. Tool Registry & MCP integration

Two tool sources, unified into one registry the execution loop calls into:

1. **Native tools** — `view_file`, `grep_search`, `run_command`, `invoke_subagent`, `send_to_subagent` — implemented directly in your engine.
2. **MCP servers** — external tool providers speaking the Model Context Protocol. An agent's `mcpServers` frontmatter field lists servers scoped to just that agent (a code-auditor doesn't need your Gmail MCP server; don't wire it in).

```python
class ToolRegistry:
    def __init__(self):
        self.native: dict[str, Callable] = {}
        self.mcp_clients: dict[str, MCPClient] = {}

    def known_names(self) -> set[str]:
        return set(self.native) | {f"{srv}.{tool}" for srv, client in self.mcp_clients.items()
                                     for tool in client.list_tools()}

    async def dispatch(self, name: str, args: dict, ctx: AgentInstance):
        decision = permission_engine.resolve(action=f"{kind_of(name)}({name})", config=ctx.permissions)
        if decision == "deny":
            return ToolResult(error="denied by policy")
        if decision == "ask":
            await bubble_to_root(ctx, name, args)  # blocks this call only
        if name in self.native:
            return await self.native[name](ctx, **args)
        server, tool = name.split(".", 1)
        return await self.mcp_clients[server].call(tool, args)
```

This is also where your **stuck-loop detection** (which you already built in `jarvis_agent_pro.py`) plugs in cleanly — wrap `dispatch` with a call-signature history per agent instance, and if the same tool+args repeats N times with no state change, kill that instance and surface it to the parent as a failure result instead of a success. Antigravity doesn't document this publicly but you already have it; keep it, it's a real gap in their public spec.

---

## 10. Workspace Manager

```python
class WorkspaceManager:
    def provision(self, parent_workspace: WorkspaceHandle, mode: str) -> WorkspaceHandle:
        if mode == "inherit":
            return parent_workspace
        if mode == "share":
            return WorkspaceHandle(path=parent_workspace.path, isolated=False)
        if mode == "branch":
            tmp = tempfile.mkdtemp(prefix="agent-wt-")
            branch_name = f"agent/{uuid4().hex[:8]}"
            subprocess.run(["git", "worktree", "add", tmp, "-b", branch_name],
                            cwd=parent_workspace.path, check=True)
            return WorkspaceHandle(path=tmp, isolated=True, branch=branch_name)

    def cleanup(self, ws: WorkspaceHandle):
        if ws.isolated:
            subprocess.run(["git", "worktree", "remove", "--force", ws.path],
                            cwd=self.repo_root, check=False)
```

Parent retains read access to all its children's worktrees at all times (for review/merge) — don't scope that away, it's how a human or the parent agent inspects a child's diff before merging it back.

---

## 11. Build order — concrete milestones

**Milestone 1 (single-agent baseline):**
`AgentInstance.run_turn` loop working end to end with one agent, no delegation. Model call → tool dispatch → loop until final text. Get this rock solid first; every bug here multiplies once you add concurrency.

**Milestone 2 (registry + static definitions):**
`.md`/YAML agent loader with load-time tool validation. Two or three hand-written agent defs (a researcher, a coder, an auditor).

**Milestone 3 (delegation, `inherit` mode only):**
`invoke_subagent` spawning a child with fresh context, synchronous for now (await the child fully before returning) — get context isolation and `synthesize_result` correct before adding concurrency, it's easier to debug one agent at a time.

**Milestone 4 (concurrency):**
Make spawning async/fire-and-forget. Parent can spawn multiple children and keep going. This is where you'll find your race conditions — test with 2 children hammering the same tool.

**Milestone 5 (permissions):**
Static allow/deny/ask config + runtime intersection inheritance. Bubble-to-root for `ask`.

**Milestone 6 (workspace isolation):**
`branch` mode with git worktrees. This is the one your current JARVIS setup is missing — prioritize it once you're doing multi-file concurrent writes.

**Milestone 7 (lifecycle + messaging):**
Idle/wake, kill+cleanup, JSONL transcript persistence, parent→child follow-up messaging.

**Milestone 8 (sandboxing):**
Process-level env/cwd restriction first, kernel-level (`bwrap`/`firejail`) once you trust it running unattended on real client work.

**Milestone 9 (guards):**
Nesting depth cap, concurrent-children cap, global live-agent cap, your existing stuck-loop detector wired into `dispatch`.

Everything past this (A2A protocol for cross-machine agent handoff, a `/teamwork-preview`-style natural-language orchestration mode, multi-surface UI) is v2. It's UX on top of the same nine primitives above — don't build it until the primitives are solid, or you'll be debugging two layers at once.

---

## What to deliberately skip copying
- Auto-updating config on launch that can wipe local settings — version your config schema, migrate explicitly, never silent-overwrite.
- Lazy tool-name validation that hangs silently — validate at load, fail loud.
- General any-to-any peer messaging before you have a concrete need for it — YAGNI, adds a lot of routing complexity for a case you probably won't hit as a solo dev.

This is genuinely close to a second version of what you've already got running with `jarvis_agent_pro.py` — the delta is mainly §6 (worktree-based workspace isolation) and §4b (permission intersection as a formal rule rather than ad hoc checks). Those two are worth building next regardless of whether you clone the rest.
