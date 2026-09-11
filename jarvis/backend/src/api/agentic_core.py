from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..services.agentic_core.registry import AgentRegistry, AgentDef
from ..services.agentic_core.engine import AgentInstance, invoke_subagent, registry_of_instances
from ..services.agentic_core.permissions import PermissionSet, PermissionConfig
from ..services.agentic_core.workspace import WorkspaceHandle
from ..services.agentic_core.bus import MessageBus, Message

router = APIRouter()

class SpawnRequest(BaseModel):
    role: str
    prompt: str
    workspace_mode: str = "inherit"

class ResolvePermissionRequest(BaseModel):
    decision: str  # allow | deny

@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_registered_agents():
    """Lists all registered agents defined in yaml markdown files."""
    r = AgentRegistry()
    agents = r.list_agents()
    return [
        {
            "name": a.name,
            "description": a.description,
            "tools": a.tools,
            "model": a.model,
            "mainAgent": a.mainAgent,
            "subagent": a.subagent,
            "commandExecutionPolicy": a.commandExecutionPolicy,
        }
        for a in agents
    ]

@router.get("/instances", response_model=List[Dict[str, Any]])
async def list_active_instances():
    """Lists all active and idle subagent execution instances."""
    res = []
    for inst in registry_of_instances.values():
        res.append({
            "id": inst.id,
            "name": inst.definition.name,
            "role": inst.definition.description,
            "state": inst.state,
            "depth": inst.depth,
            "parent_id": inst.parent_id,
            "children": inst.children,
            "workspace": str(inst.workspace.path),
            "workspace_mode": inst.workspace.mode,
            "message_count": len(inst.messages),
        })
    return res

@router.post("/spawn", status_code=status.HTTP_201_CREATED)
async def spawn_agent_instance(data: SpawnRequest):
    """Spawns a new root AgentInstance to execute a task."""
    r = AgentRegistry()
    try:
        agent_def = r.get_agent(data.role)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Construct top-level root workspace
    workspace = WorkspaceHandle(
        path=Path.cwd().resolve(),
        mode="inherit",
        isolated=False
    )

    # Root permissions from system configurations
    permissions = PermissionSet(
        config=PermissionConfig(
            allow=["*"],
            deny=[],
            ask=[]
        ),
        command_execution="sandbox",
        sandbox_enabled=True,
        workspace_root=Path.cwd().resolve()
    )

    import uuid
    instance_id = str(uuid.uuid4())

    instance = AgentInstance(
        id=instance_id,
        definition=agent_def,
        state="running",
        messages=[],
        parent_id=None,
        children=[],
        workspace=workspace,
        depth=0,
        permissions=permissions
    )

    registry_of_instances[instance_id] = instance

    # Run the turn in a non-blocking background task
    import asyncio
    asyncio.create_task(instance.run_turn(Message(role="user", content=data.prompt)))

    return {
        "success": True,
        "instance_id": instance_id,
        "name": agent_def.name,
        "message": f"Successfully spawned root agent '{agent_def.name}' on your task."
    }

@router.get("/instances/{instance_id}/transcript", response_model=List[Dict[str, Any]])
async def get_instance_transcript(instance_id: str):
    """Retrieves the full message history (transcript) of a given agent instance."""
    inst = registry_of_instances.get(instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Agent instance not found.")

    return [
        {
            "role": m.role,
            "content": m.content,
            "meta": m.meta
        }
        for m in inst.messages
    ]

@router.post("/instances/{instance_id}/kill")
async def kill_instance(instance_id: str):
    """Gracefully terminates a running agent instance and cleans up its workspace."""
    inst = registry_of_instances.get(instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Agent instance not found.")

    inst.kill()
    return {"success": True, "message": f"Successfully killed agent instance {instance_id}."}

@router.post("/permission-requests/{request_id}/resolve")
async def resolve_permission_request(request_id: str, data: ResolvePermissionRequest):
    """Resolves a human-in-the-loop permission request bubbling to root."""
    bus = MessageBus()
    bus.resolve_permission_request(request_id, data.decision)
    return {"success": True, "message": f"Successfully resolved permission request with decision: {data.decision}."}
