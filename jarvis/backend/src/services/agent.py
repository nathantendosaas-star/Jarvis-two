"""AgentService — CRUD operations for the Agent workforce database table."""

import uuid
import json
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.agent import Agent
from ..schemas.agent import AgentCreate, AgentUpdate
from ..core.events import event_broker


def _encode(value: list | None) -> str:
    """Serialize a Python list to a JSON string for SQLite storage."""
    return json.dumps(value or [])


class AgentService:

    @staticmethod
    async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
        import uuid
        from pathlib import Path
        from datetime import datetime, timezone

        agent_id = str(uuid.uuid4())

        # Initialize context cache files
        cached_dir = Path("Cached")
        cached_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_clean = data.name.replace(" ", "_")

        tasks_filename = f"{name_clean}_{agent_id[:8]}_{timestamp}_tasks.md"
        history_filename = f"{name_clean}_{agent_id[:8]}_{timestamp}_history.md"
        progress_filename = f"{name_clean}_{agent_id[:8]}_{timestamp}_progress.md"

        tasks_path = cached_dir / tasks_filename
        history_path = cached_dir / history_filename
        progress_path = cached_dir / progress_filename

        tasks_content = f"""# Assigned Tasks for {data.name}
Created: {datetime.now(timezone.utc).isoformat()}
Role: {data.role}

## Tasks
- [ ] Initialize system and capabilities
"""
        history_content = f"""# History Log for {data.name}
Created: {datetime.now(timezone.utc).isoformat()}

## Activity History
- [{datetime.now(timezone.utc).isoformat()}] Agent node initialized and workspace cache created.
"""
        progress_content = f"""# Progress Status for {data.name}
Created: {datetime.now(timezone.utc).isoformat()}

## Status
- **Current Task**: Initialized
- **Overall Progress**: 100%
- **Status**: Ready
"""

        try:
            tasks_path.write_text(tasks_content, encoding="utf-8")
            history_path.write_text(history_content, encoding="utf-8")
            progress_path.write_text(progress_content, encoding="utf-8")
        except Exception:
            pass

        agent = Agent(
            id=agent_id,
            name=data.name,
            role=data.role,
            avatar=data.avatar,
            status=data.status,
            current_task=data.current_task,
            priority=data.priority,
            cpu_allocation=data.cpu_allocation,
            memory_allocation=data.memory_allocation,
            capabilities=_encode(data.capabilities),
            tools=_encode(data.tools),
            activity=_encode(data.activity),
            performance=data.performance,
        )
        db.add(agent)
        await db.flush()
        await event_broker.publish("AgentCreated", {"agent_id": agent.id, "name": agent.name})
        return agent

    @staticmethod
    async def get_agents(db: AsyncSession) -> List[Agent]:
        result = await db.execute(select(Agent).order_by(desc(Agent.created_at)))
        return list(result.scalars().all())

    @staticmethod
    async def get_agent(db: AsyncSession, agent_id: str) -> Optional[Agent]:
        return await db.get(Agent, agent_id)

    @staticmethod
    async def update_agent(db: AsyncSession, agent_id: str, data: AgentUpdate) -> Optional[Agent]:
        agent = await db.get(Agent, agent_id)
        if not agent:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Lists must be re-serialized to JSON before writing
        for list_field in ("capabilities", "tools", "activity"):
            if list_field in update_data:
                update_data[list_field] = _encode(update_data[list_field])

        for key, value in update_data.items():
            setattr(agent, key, value)

        await db.flush()
        await event_broker.publish("AgentUpdated", {
            "agent_id": agent.id,
            "status": agent.status,
            "priority": agent.priority,
        })
        return agent

    @staticmethod
    async def delete_agent(db: AsyncSession, agent_id: str, delete_cache: bool = False) -> bool:
        agent = await db.get(Agent, agent_id)
        if not agent:
            return False

        if delete_cache:
            from pathlib import Path
            cached_dir = Path("Cached")
            if cached_dir.exists():
                name_clean = agent.name.replace(" ", "_")
                for f in cached_dir.iterdir():
                    if f.is_file():
                        if agent_id in f.name or agent_id[:8] in f.name or (name_clean and name_clean in f.name):
                            try:
                                f.unlink()
                            except Exception:
                                pass

        await db.delete(agent)
        await db.flush()
        await event_broker.publish("AgentDecommissioned", {"agent_id": agent_id})
        return True
