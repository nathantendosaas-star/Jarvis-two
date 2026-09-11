import pytest
import asyncio
from pathlib import Path
from backend.src.services.agentic_core.engine import AgentInstance, invoke_subagent, registry_of_instances
from backend.src.services.agentic_core.registry import AgentRegistry, AgentDef
from backend.src.services.agentic_core.permissions import PermissionSet, PermissionConfig
from backend.src.services.agentic_core.workspace import WorkspaceHandle

# Stub run_turn to avoid actual LLM calls during integration tests
async def stub_run_turn(self, incoming):
    self.state = "idle"

@pytest.mark.asyncio
async def test_subagent_invocation_integration(monkeypatch):
    monkeypatch.setattr(AgentInstance, "run_turn", stub_run_turn)

    # Setup parent instance
    parent_def = AgentDef(
        name="coder",
        description="Software Engineer Subagent",
        tools=["view_file", "write_file", "invoke_subagent"],
        model="flash"
    )
    parent_workspace = WorkspaceHandle(
        path=Path.cwd().resolve(),
        mode="inherit",
        isolated=False
    )
    parent_permissions = PermissionSet(
        config=PermissionConfig(allow=["*"], deny=[], ask=[]),
        command_execution="sandbox",
        sandbox_enabled=True,
        workspace_root=Path.cwd().resolve()
    )

    parent_instance = AgentInstance(
        id="parent-test-id",
        definition=parent_def,
        state="idle",
        messages=[],
        parent_id=None,
        children=[],
        workspace=parent_workspace,
        depth=0,
        permissions=parent_permissions
    )

    registry_of_instances[parent_instance.id] = parent_instance

    # Spawning the subagent 'researcher'
    child_id = await invoke_subagent(
        caller=parent_instance,
        role="researcher",
        prompt="Auditing the repository structure.",
        workspace_mode="share"
    )

    assert child_id is not None
    assert child_id in parent_instance.children
    assert child_id in registry_of_instances

    child_instance = registry_of_instances[child_id]
    assert child_instance.parent_id == parent_instance.id
    assert child_instance.depth == 1
    assert child_instance.workspace.mode == "share"
    assert not child_instance.workspace.isolated

    # Check permissions intersection:
    # Researcher only has "view_file" and "grep_search" in definition.
    # Its execution policy is "off". Therefore, "command(git status)" should be "deny"
    assert child_instance.permissions.resolve("command(git status)") == "deny"
    assert child_instance.permissions.resolve("file(src/App.tsx)") == "allow" or child_instance.permissions.resolve("file(src/App.tsx)") == "ask"

    # Clean up
    child_instance.kill()
    parent_instance.kill()
