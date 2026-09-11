import os
import uuid
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any

from google import genai
from google.genai import types

from ...core.config import get_settings
from .registry import AgentDef, AgentRegistry
from .permissions import PermissionSet, PermissionConfig, intersect_permissions, load_permission_config
from .workspace import WorkspaceHandle, WorkspaceManager
from .bus import Message, MessageBus, synthesize_result
from .tools import ToolRegistry
from .guards import check_spawn_allowed, NestingLimitExceeded, TooManyChildren, GlobalAgentLimitExceeded

# Global registry of active and dead agent instances
registry_of_instances: Dict[str, 'AgentInstance'] = {}

class DeadAgentError(Exception):
    pass

class AgentInstance:
    def __init__(
        self,
        id: str,
        definition: AgentDef,
        state: Literal["running", "idle", "killed"],
        messages: List[Message],
        parent_id: Optional[str],
        children: List[str],
        workspace: WorkspaceHandle,
        depth: int,
        permissions: PermissionSet
    ):
        self.id = id
        self.definition = definition
        self.state = state
        self.messages = messages
        self.parent_id = parent_id
        self.children = children
        self.workspace = workspace
        self.depth = depth
        self.permissions = permissions

        # Stuck-loop call history fingerprint tracking
        self.call_history: List[str] = []

        # Lifecycle queue for inbox messages while running
        self.pending_inbox: List[Message] = []

        # Self registration
        bus = MessageBus()
        bus.register(self.id, self)

        # Ensure transcript log path exists
        self.transcript_dir = self.workspace.path / ".agents" / "transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_file = self.transcript_dir / f"{self.id}.jsonl"

    def log_message(self, role: str, content: str, meta: Optional[dict] = None):
        """Appends a single message turn to the persistent JSONL audit trail on disk."""
        entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "role": role,
            "content": content,
            "meta": meta or {}
        }
        try:
            with open(self.transcript_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Error logging transcript entry: {e}")

    async def receive(self, msg: Message):
        """Auto-wakes idle agent or buffers messages into pending queue if currently running."""
        if self.state == "killed":
            raise DeadAgentError("This agent instance has been killed and cannot receive messages.")

        if self.state == "idle":
            self.log_message("user", msg.content, msg.meta)
            await self.run_turn(msg)
        elif self.state == "running":
            self.pending_inbox.append(msg)

    async def run_turn(self, incoming: Optional[Message]):
        """Executes the core cognitive LLM loop with tool-calling and response synthesis."""
        self.state = "running"
        if incoming:
            self.messages.append(incoming)

        settings = get_settings()
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Resolve model tag
        model_name = self.definition.model
        if model_name == "inherit":
            model_tag = "gemini-2.5-flash"
        elif model_name == "flash":
            model_tag = "gemini-2.5-flash"
        else:
            model_tag = "gemini-2.5-pro"

        # Compile standard tools for Gemini
        tool_registry = ToolRegistry()
        gemini_tools = []

        # Register tools in standard format
        for tool_name in self.definition.tools:
            if tool_name == "view_file":
                gemini_tools.append(types.FunctionDeclaration(
                    name="view_file",
                    description="Read the contents of a file in the workspace.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "path": types.Schema(type=types.Type.STRING, description="Relative path of file to read.")
                        },
                        required=["path"]
                    )
                ))
            elif tool_name == "write_file":
                gemini_tools.append(types.FunctionDeclaration(
                    name="write_file",
                    description="Write full content to a file in the workspace.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "path": types.Schema(type=types.Type.STRING, description="Relative file path."),
                            "content": types.Schema(type=types.Type.STRING, description="Content to write.")
                        },
                        required=["path", "content"]
                    )
                ))
            elif tool_name == "grep_search":
                gemini_tools.append(types.FunctionDeclaration(
                    name="grep_search",
                    description="Perform high-performance regex search across workspace files.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "pattern": types.Schema(type=types.Type.STRING, description="Regex pattern.")
                        },
                        required=["pattern"]
                    )
                ))
            elif tool_name == "run_command":
                gemini_tools.append(types.FunctionDeclaration(
                    name="run_command",
                    description="Run a shell or terminal command in the workspace.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "command": types.Schema(type=types.Type.STRING, description="Shell command to run.")
                        },
                        required=["command"]
                    )
                ))
            elif tool_name == "invoke_subagent":
                gemini_tools.append(types.FunctionDeclaration(
                    name="invoke_subagent",
                    description="Spawns an isolated specialized subagent to perform a subtask.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "role": types.Schema(type=types.Type.STRING, description="Name of agent definition from registry."),
                            "prompt": types.Schema(type=types.Type.STRING, description="Instruction prompt for subagent."),
                            "workspace_mode": types.Schema(
                                type=types.Type.STRING,
                                description="inherit | branch | share"
                            )
                        },
                        required=["role", "prompt"]
                    )
                ))
            elif tool_name == "send_to_subagent":
                gemini_tools.append(types.FunctionDeclaration(
                    name="send_to_subagent",
                    description="Send a message/followup instruction to an active subagent.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "child_id": types.Schema(type=types.Type.STRING, description="Subagent instance UUID."),
                            "message": types.Schema(type=types.Type.STRING, description="Message string.")
                        },
                        required=["child_id", "message"]
                    )
                ))

        # Build contents sequence
        contents = []
        for m in self.messages:
            role = "user" if m.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))

        config = types.GenerateContentConfig(
            system_instruction=self.definition.system_prompt,
            temperature=0.2,
            tools=[types.Tool(function_declarations=gemini_tools)] if gemini_tools else []
        )

        try:
            while True:
                response = await client.aio.models.generate_content(
                    model=model_tag,
                    contents=contents,
                    config=config
                )

                # Retrieve first candidate content parts
                response_parts = response.candidates[0].content.parts if response.candidates else []
                text_content = response.text or ""

                # Construct models response content turn
                model_parts = []
                function_calls_found = []

                for part in response_parts:
                    if hasattr(part, "function_call") and part.function_call:
                        function_calls_found.append(part.function_call)
                    model_parts.append(part)

                model_message = Message(role="model", content=text_content)
                self.messages.append(model_message)
                self.log_message("model", text_content)
                contents.append(types.Content(role="model", parts=model_parts))

                if not function_calls_found:
                    # Final text response arrived, we are done
                    break

                # Process each tool call sequentially
                function_response_parts = []
                for fc in function_calls_found:
                    call_args = dict(fc.args) if fc.args else {}

                    # Log execution
                    self.log_message("system", f"Executing tool: {fc.name} with args: {call_args}")

                    # Call tool registry
                    result_str = await tool_registry.dispatch(fc.name, call_args, self)

                    self.log_message("system", f"Tool Result: {result_str[:200]}")

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result_str}
                        )
                    )

                # Append tool results as user input and loop back
                contents.append(types.Content(role="user", parts=function_response_parts))
                self.messages.append(Message(role="user", content=json.dumps([p.function_response for p in function_response_parts])))

        except Exception as e:
            err_msg = f"Model loop error: {e}"
            self.messages.append(Message(role="model", content=err_msg))
            self.log_message("model", err_msg)

        self.state = "idle"

        # Message Bus notification on task completion (or turn completion)
        if self.parent_id:
            bus = MessageBus()
            # Synthesize results
            summary = await synthesize_result(self.messages)
            await bus.send(to=self.parent_id, from_=self.id, content=summary, meta={"subagent_completed": True})

        # Process any pending queue messages
        if self.pending_inbox:
            next_msg = self.pending_inbox.pop(0)
            await self.receive(next_msg)

    def kill(self):
        """Gracefully kills the agent instance, cleaning up workspaces and worktrees."""
        self.state = "killed"

        # Workspace cleanup
        ws_mgr = WorkspaceManager()
        asyncio.create_task(ws_mgr.cleanup(self.workspace))

        # Unregister from bus
        bus = MessageBus()
        bus.unregister(self.id)


async def invoke_subagent(
    caller: AgentInstance,
    role: str,
    prompt: str,
    workspace_mode: str = "inherit",
    model_override: Optional[str] = None
) -> str:
    """Spawns an isolated specialized child agent in the agentic loop hierarchy."""
    # 1. Enforce Nesting and resource limit guards
    live_agents = sum(1 for a in registry_of_instances.values() if a.state != "killed")
    check_spawn_allowed(caller.depth, len(caller.children), live_agents)

    # 2. Get Agent Definition
    registry = AgentRegistry()
    agent_def = registry.get_agent(role)
    if not agent_def.subagent:
        raise PermissionError(f"Agent definition '{role}' is explicitly configured to not allow subagent spawning.")

    child_id = str(uuid.uuid4())

    # 3. Provision isolated Workspace
    ws_mgr = WorkspaceManager()
    workspace = await ws_mgr.provision(
        parent_workspace=caller.workspace,
        mode=workspace_mode,
        child_id=child_id
    )

    # 4. Resolve intersected permissions
    child_permissions = intersect_permissions(
        parent=caller.permissions,
        child_declared_config=PermissionConfig(
            allow=agent_def.tools,
            deny=[],
            ask=["*"]
        ),
        child_command_policy=agent_def.commandExecutionPolicy
    )

    # 5. Build AgentInstance
    child = AgentInstance(
        id=child_id,
        definition=agent_def,
        state="running",
        messages=[],  # Fresh, isolated clean slate behavior
        parent_id=caller.id,
        children=[],
        workspace=workspace,
        depth=caller.depth + 1,
        permissions=child_permissions
    )

    # 6. Save reference and launch turn background tasks
    registry_of_instances[child_id] = child
    caller.children.append(child_id)

    # Non-blocking concurrent execution fire-and-forget
    asyncio.create_task(child.run_turn(Message(role="user", content=prompt)))

    return child_id
