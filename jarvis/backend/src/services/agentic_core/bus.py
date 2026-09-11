import json
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class Message(BaseModel):
    role: str  # user | model | system
    content: str
    meta: Dict[str, Any] = {}

class MessageBus:
    _instance: Optional['MessageBus'] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MessageBus, cls).__new__(cls, *args, **kwargs)
            cls._instance.instances = {}
            cls._instance.permission_responses = {}
        return cls._instance

    def register(self, agent_id: str, instance: Any):
        """Registers a live agent instance to the bus."""
        self.instances[agent_id] = instance

    def unregister(self, agent_id: str):
        """Unregisters an agent instance from the bus."""
        self.instances.pop(agent_id, None)

    async def send(self, to: str, from_: str, content: str, meta: Optional[Dict[str, Any]] = None):
        """Sends a message to a specific agent instance."""
        target = self.instances.get(to)
        if not target:
            raise ValueError(f"Target agent {to} is not registered or is offline.")

        # Deliver message to target
        m = Message(role="user", content=content, meta={"from": from_, **(meta or {})})
        await target.receive(m)

    async def request_permission(self, agent_id: str, root_id: str, action: str, details: Dict[str, Any]) -> str:
        """Publishes a permission request and blocks until human approval or timeout."""
        request_id = f"req-{uuid_hash(action)}"
        self.permission_responses[request_id] = asyncio.Event()
        self.permission_responses[f"{request_id}-data"] = None

        # Here we would publish a WebSocket/Event notification to the frontend.
        # For simplicity, we also log it and listen for complete event.
        print(f"Permission requested by agent {agent_id} (root: {root_id}) for action: {action}. Request ID: {request_id}")

        # We block and wait
        try:
            # Wait up to 300 seconds (5 mins) for human response
            await asyncio.wait_for(self.permission_responses[request_id].wait(), timeout=300.0)
            decision = self.permission_responses[f"{request_id}-data"]
            return decision or "deny"
        except asyncio.TimeoutError:
            print(f"Permission request {request_id} timed out. Defaulting to deny.")
            return "deny"
        finally:
            self.permission_responses.pop(request_id, None)
            self.permission_responses.pop(f"{request_id}-data", None)

    def resolve_permission_request(self, request_id: str, decision: str):
        """Called by the API controller when a user responds to a permission request."""
        event = self.permission_responses.get(request_id)
        if event:
            self.permission_responses[f"{request_id}-data"] = decision
            event.set()

def uuid_hash(text: str) -> str:
    import uuid
    import hashlib
    h = hashlib.md5(text.encode('utf-8')).hexdigest()
    return h[:8]


async def synthesize_result(messages: List[Message]) -> str:
    """Summarizes the child agent's message history into a clean outcome description."""
    from ..ai import AIService

    ai_service = AIService()
    history = []
    # Use first N-1 messages as history
    for m in messages[:-1]:
        history.append({
            "role": "user" if m.role == "user" else "model",
            "content": m.content
        })

    last_content = messages[-1].content if messages else "No output produced."

    system_instr = "Summarize the outcome of this task in 3-5 sentences for your supervisor. Include any files changed and any blockers."

    try:
        response_chunks = []
        async for chunk in ai_service.stream_chat(
            message=f"Please summarize our final results. Here was our last model turn: {last_content}",
            history=history,
            system_instruction=system_instr,
            model="gemini-3.1-flash-lite"
        ):
            if "text" in chunk:
                response_chunks.append(chunk["text"])

        return "".join(response_chunks).strip() or "Task completed."
    except Exception as e:
        return f"Task completed. (Summary generation failed: {e})"
