import pytest
import asyncio
from pathlib import Path
from backend.src.services.agentic_core.permissions import PermissionSet, PermissionConfig, intersect_permissions, load_permission_config
from backend.src.services.agentic_core.sandbox import check_command_safety, get_scrubbed_environment
from backend.src.services.agentic_core.workspace import WorkspaceManager, WorkspaceHandle
from backend.src.services.agentic_core.guards import check_spawn_allowed, NestingLimitExceeded, TooManyChildren, GlobalAgentLimitExceeded
from backend.src.services.agentic_core.bus import MessageBus, Message
from backend.src.services.agentic_core.registry import AgentRegistry

@pytest.mark.asyncio
async def test_permission_engine():
    config = PermissionConfig(
        allow=["command(git status)", "file(src/.*)"],
        deny=["command(rm -rf.*)"],
        ask=["*"]
    )
    p_set = PermissionSet(config=config)

    # 1. Deny resolution
    assert p_set.resolve("command(rm -rf /)") == "deny"
    # 2. Allow resolution
    assert p_set.resolve("command(git status)") == "allow"
    # 3. Ask fallback
    assert p_set.resolve("command(git commit)") == "ask"

    # Test intersection
    parent_config = PermissionConfig(allow=["command(git status)"], deny=[], ask=["*"])
    parent = PermissionSet(config=parent_config, command_execution="auto")

    child_declared = PermissionConfig(allow=["command(rm -rf /)"], deny=[], ask=["*"])
    intersected = intersect_permissions(parent, child_declared, "sandbox")

    # Child's declared command(rm -rf /) should be intersection-denied or downgraded to parent's policy (ask/deny)
    assert intersected.resolve("command(rm -rf /)") == "deny" or intersected.resolve("command(rm -rf /)") == "ask"

def test_sandbox_safety():
    # Detect blocked commands
    is_safe, msg = check_command_safety("rm -rf /", Path.cwd())
    assert not is_safe
    assert "Blocked pattern" in msg

    # Detect relative path traversals escaping workspace
    is_safe_trav, msg_trav = check_command_safety("cat ../../../etc/passwd", Path.cwd())
    assert not is_safe_trav
    assert "Relative path traversal" in msg_trav

    # Verify environment scrubbing
    env = get_scrubbed_environment()
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "DATABASE_URL" in env or "PATH" in env

@pytest.mark.asyncio
async def test_workspace_modes():
    mgr = WorkspaceManager()
    parent_path = Path.cwd().resolve()
    parent_handle = WorkspaceHandle(path=parent_path, mode="inherit", isolated=False)

    # Test inherit
    ws_inherit = await mgr.provision(parent_handle, "inherit", "child-1")
    assert ws_inherit.path == parent_path
    assert not ws_inherit.isolated

    # Test share
    ws_share = await mgr.provision(parent_handle, "share", "child-2")
    assert ws_share.path == parent_path
    assert not ws_share.isolated

def test_guards():
    # Enforce nesting depths
    with pytest.raises(NestingLimitExceeded):
        check_spawn_allowed(caller_depth=10, caller_children_count=2, live_agents_count=5)

    # Enforce children per parent
    with pytest.raises(TooManyChildren):
        check_spawn_allowed(caller_depth=3, caller_children_count=8, live_agents_count=5)

    # Enforce global capacity
    with pytest.raises(GlobalAgentLimitExceeded):
        check_spawn_allowed(caller_depth=3, caller_children_count=2, live_agents_count=50)

@pytest.mark.asyncio
async def test_agent_registry():
    r = AgentRegistry()
    agents = r.list_agents()
    assert len(agents) >= 3
    names = [a.name for a in agents]
    assert "coder" in names
    assert "researcher" in names
    assert "code-auditor" in names
