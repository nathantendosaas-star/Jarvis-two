"""JARVIS AI OS — FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, async_session
from .core.seeder import seed_agents
from .models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup, seed defaults, dispose engine on shutdown."""
    from pathlib import Path
    Path("Cached").mkdir(exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite create_all does not evolve existing tables; these columns are additive.
        for statement in (
            "ALTER TABLE memories ADD COLUMN memory_type VARCHAR(32) DEFAULT 'project'",
            "ALTER TABLE memories ADD COLUMN scope VARCHAR(64) DEFAULT 'project'",
            "ALTER TABLE memories ADD COLUMN lineage TEXT DEFAULT '{}'",
            "ALTER TABLE memories ADD COLUMN retrieval_metadata TEXT DEFAULT '{}'",
            "ALTER TABLE memories ADD COLUMN retrieval_count INTEGER DEFAULT 0",
            "ALTER TABLE memories ADD COLUMN last_retrieved_at DATETIME",
        ):
            try:
                await conn.execute(text(statement))
            except Exception:
                pass
    # Seed default workforce if empty
    async with async_session() as db:
        seeded = await seed_agents(db)
        if seeded:
            print(f"[JARVIS] Seeded {seeded} default agents into workforce.")
    yield
    await engine.dispose()


app = FastAPI(title="JARVIS AI OS", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Router imports ---
from .api import auth, projects, chats, files, tasks, memories, settings, agents, events, jobs, agentic_core, automations  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(memories.router, prefix="/api/memories", tags=["memories"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(agentic_core.router, prefix="/api/agentic-core", tags=["agentic-core"])
app.include_router(automations.router, prefix="/api/automations", tags=["automations"])


# Compatibility routes used by the Vite frontend during local development.
import json  # noqa: E402
from fastapi import Depends  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from .core.config import get_settings  # noqa: E402
from .dependencies import get_ai_service, get_db  # noqa: E402
from .services.ai import AIService  # noqa: E402


class FrontendChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []
    systemInstruction: str | None = None
    useSearch: bool = False
    model: str | None = "gemini-3.1-flash-lite"


class TranscribeRequest(BaseModel):
    audioData: str
    mimeType: str = "audio/webm"


@app.get("/api/config")
async def frontend_config():
    settings = get_settings()
    return {"hasApiKey": bool(settings.GEMINI_API_KEY), "appUrl": settings.APP_URL}


def is_research_request(message: str) -> bool:
    msg_lower = message.lower()
    keywords = ["research", "find information on", "investigate", "gather info", "collect data", "search for"]
    return any(keyword in msg_lower for keyword in keywords)


def extract_research_topic(message: str) -> str:
    msg_lower = message.lower()
    prefixes = [
        "help research ",
        "please research ",
        "research ",
        "find information on ",
        "investigate ",
        "gather info on ",
        "collect data on ",
        "search for "
    ]
    for prefix in prefixes:
        if msg_lower.startswith(prefix):
            return message[len(prefix):].strip()
    return message.strip()


async def research_flow_generator(message: str, db):
    import asyncio
    import uuid
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from .models.agent import Agent
    from .services.ai import AIService

    topic = extract_research_topic(message)
    agent_id = str(uuid.uuid4())
    task_id = agent_id[:8]
    clean_topic_filename = "".join(c if c.isalnum() or c in " _-" else "_" for c in topic)[:40].strip().replace(" ", "_")
    agent_name = f"Researcher-{topic[:30]}"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cached_dir = Path("Cached")
    cached_dir.mkdir(exist_ok=True)
    specs_dir = cached_dir / "research_specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    spec_filename = f"{clean_topic_filename}_{task_id}_{timestamp}_spec.md"
    tasks_filename = f"{clean_topic_filename}_{task_id}_{timestamp}_tasks.md"
    history_filename = f"{clean_topic_filename}_{task_id}_{timestamp}_history.md"
    progress_filename = f"{clean_topic_filename}_{task_id}_{timestamp}_progress.md"

    spec_path = specs_dir / spec_filename
    tasks_path = cached_dir / tasks_filename
    history_path = cached_dir / history_filename
    progress_path = cached_dir / progress_filename

    # Register initial agent in database
    new_agent = Agent(
        id=agent_id,
        name=agent_name,
        role="Deep Research Specialist",
        avatar="🔍",
        status="working",
        current_task=f"Researching: {topic}",
        priority="high",
        cpu_allocation=70,
        memory_allocation=256,
        capabilities=json.dumps(["Deep Research", "Market Intelligence", "OpenRouter Synthesis"]),
        tools=json.dumps(["web_fetch", "write_file_content", "save_memory"]),
        activity=json.dumps([f"Node initialized for task: {topic}"]),
        performance=100
    )
    db.add(new_agent)
    await db.commit()

    yield f"data: {json.dumps({'text': f'🤖 **JARVIS CEO Orchestrator**: Research directive recognized for: \"{topic}\".\n\n*Stage 1: Gemini CEO generating comprehensive Research Spec (`Cached/research_specs/{spec_filename}`)...*\n\n'})}\n\n"
    yield f"data: {json.dumps({'workspaceChanged': agent_id})}\n\n"

    ai_service = AIService()

    # -----------------------------------------------------------------------
    # STAGE 1: Gemini CEO Generates Structured Research Specification
    # -----------------------------------------------------------------------
    ceo_prompt = f"""You are the JARVIS CEO Orchestrator. Create a detailed, actionable Research Specification for a researcher subagent on:
Topic: "{topic}"

Include:
1. Executive Summary & Core Objectives
2. Key Investigation Questions
3. Suggested Search Vectors & Fact-Verification Criteria
4. Target Deliverables & Report Structure

Write clear Markdown formatting without raw asterisks."""

    ceo_spec_chunks = []
    try:
        async for chunk in ai_service.stream_chat(
            message=ceo_prompt,
            history=[],
            system_instruction="You are the JARVIS CEO Orchestrator generating high-level structured specifications.",
            model="gemini-3.1-flash-lite",
            db=db
        ):
            if "text" in chunk:
                ceo_spec_chunks.append(chunk["text"])
    except Exception as e:
        ceo_spec_chunks = [f"# Research Spec: {topic}\n\nObjectives: Investigate and compile comprehensive report on {topic}."]

    spec_content = "".join(ceo_spec_chunks)
    spec_path.write_text(spec_content, encoding="utf-8")

    yield f"data: {json.dumps({'text': f'📋 **CEO Research Spec Generated**:\n- Saved to `Cached/research_specs/{spec_filename}`\n\n*Stage 2: Spawning OpenRouter DeepSeek v4 Flash Researcher strictly following specification...*\n\n'})}\n\n"
    await asyncio.sleep(1.0)

    # Initialize tracking cache files
    tasks_content = f"""# Assigned Tasks for {agent_name}
Created: {datetime.now(timezone.utc).isoformat()}
Role: OpenRouter Research Specialist
Spec Reference: Cached/research_specs/{spec_filename}

## Tasks
- [x] Receive CEO research spec: "{topic}"
- [ ] Execute search and deep verification via OpenRouter DeepSeek
- [ ] Synthesize empirical findings
- [ ] Generate comprehensive final report
"""
    history_content = f"""# History Log for {agent_name}
Created: {datetime.now(timezone.utc).isoformat()}

## Activity History
- [{datetime.now(timezone.utc).isoformat()}] CEO Spec generated and assigned to OpenRouter DeepSeek researcher.
"""
    progress_content = f"""# Progress Status for {agent_name}
Created: {datetime.now(timezone.utc).isoformat()}

## Status
- **Current Task**: Executing Stage 2 DeepSeek Research on "{topic}"
- **Overall Progress**: 35%
- **Status**: Researching
"""
    tasks_path.write_text(tasks_content, encoding="utf-8")
    history_path.write_text(history_content, encoding="utf-8")
    progress_path.write_text(progress_content, encoding="utf-8")

    # -----------------------------------------------------------------------
    # STAGE 2: OpenRouter DeepSeek Researcher Executes Spec
    # -----------------------------------------------------------------------
    research_prompt = f"""You are {agent_name}, a specialized Research Agent powered by DeepSeek v4 Flash.
You must strictly follow the CEO Research Specification below to conduct thorough research and create the final deliverable.

=== CEO RESEARCH SPECIFICATION ===
{spec_content}
==================================

Topic: "{topic}"

Please produce a comprehensive, structured research report with citations, clear headings, key takeaways, and conclusions.

Also, generate the updated contents for the three cache files based on your execution details:
1. TASKS: A checklist of the tasks performed.
2. HISTORY: A timeline of the actions taken.
3. PROGRESS: A progress report of the status.

Format your output EXACTLY as follows:
---REPORT---
[Your detailed report findings here]
---TASKS---
[Your tasks.md content here]
---HISTORY---
[Your history.md content here]
---PROGRESS---
[Your progress.md content here]
"""

    response_chunks = []
    try:
        async for chunk in ai_service.stream_chat(
            message=research_prompt,
            history=[],
            system_instruction=f"You are {agent_name}, an elite research subagent executing a CEO research specification using DeepSeek v4 Flash.",
            model="deepseek/deepseek-v4-flash",
            db=db
        ):
            if "text" in chunk:
                response_chunks.append(chunk["text"])
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Failed to run OpenRouter research: {str(e)}'})}\n\n"
        return

    full_response = "".join(response_chunks)

    report_content = "Research report generation completed."
    tasks_update = tasks_content
    history_update = history_content
    progress_update = progress_content

    if "---REPORT---" in full_response:
        parts = full_response.split("---REPORT---")[1].split("---TASKS---")
        report_content = parts[0].strip()
        if len(parts) > 1:
            parts2 = parts[1].split("---HISTORY---")
            tasks_update = parts2[0].strip()
            if len(parts2) > 1:
                parts3 = parts2[1].split("---PROGRESS---")
                history_update = parts3[0].strip()
                if len(parts3) > 1:
                    progress_update = parts3[1].strip()

    tasks_path.write_text(tasks_update, encoding="utf-8")
    history_path.write_text(history_update, encoding="utf-8")
    progress_path.write_text(progress_update, encoding="utf-8")

    report_filename = f"{clean_topic_filename}_{task_id}_{timestamp}_report.md"
    report_path = cached_dir / report_filename
    report_path.write_text(report_content, encoding="utf-8")

    # Update agent to idle
    from sqlalchemy import select
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if db_agent:
        db_agent.status = "idle"
        db_agent.current_task = None
        db_agent.activity = json.dumps([
            f"Completed 2-stage research on {topic}",
            f"Spec: Cached/research_specs/{spec_filename}",
            f"Report: Cached/{report_filename}"
        ])
        await db.commit()

    yield f"data: {json.dumps({'workspaceChanged': agent_id})}\n\n"

    yield f"data: {json.dumps({'notification': {
        'title': 'Research Complete',
        'message': f'DeepSeek researcher completed research on {topic}. Findings cached in Cached/.',
        'type': 'success'
    }})}\n\n"

    yield f"data: {json.dumps({'text': f'📡 **Ping from {agent_name}**:\n*Status: Done!*\n\n✅ **Research Task Successfully Completed via OpenRouter DeepSeek!**\n\nThe delegated agent **{agent_name}** has completed the research on: **{topic}** following the CEO Specification.\n\nAll findings and logs have been cached:\n- `Cached/research_specs/{spec_filename}`\n- `Cached/{report_filename}`\n- `Cached/{tasks_filename}`\n- `Cached/{history_filename}`\n- `Cached/{progress_filename}`\n\nYou can view these markdown files under the **Files** tab!\n\nA notification has also been sent to your JARVIS notification system.'})}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def frontend_chat(
    data: FrontendChatRequest,
    ai_service: AIService = Depends(get_ai_service),
    db=Depends(get_db),
):
    """Streaming chat endpoint with integrated JARVIS function-calling tool loop."""
    if is_research_request(data.message):
        return StreamingResponse(research_flow_generator(data.message, db), media_type="text/event-stream")

    async def event_generator():
        async for chunk in ai_service.stream_chat(
            message=data.message,
            history=data.history,
            system_instruction=data.systemInstruction
            or "You are JARVIS, an advanced AI Operating System. Answer elegantly, with a technical, refined, and helpful persona. You can create projects, agents, tasks, and save memories using your available tools.",
            model=data.model or "gemini-3.1-flash-lite",
            use_search=data.useSearch,
            db=db,
        ):
            if "error" in chunk:
                yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                return
            if chunk.get("done"):
                yield "data: [DONE]\n\n"
                return
            if "workspaceChanged" in chunk:
                yield f"data: {json.dumps({'workspaceChanged': chunk['workspaceChanged']})}\n\n"
                continue
            if "toolCall" in chunk:
                yield f"data: {json.dumps({'toolCall': chunk['toolCall']})}\n\n"
                continue

            search_chunks = [
                {"web": {"uri": c.get("uri", ""), "title": c.get("title", "")}}
                for c in chunk.get("searchChunks", [])
            ]
            yield f"data: {json.dumps({'text': chunk.get('text', ''), 'searchChunks': search_chunks})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/transcribe")
async def frontend_transcribe(
    data: TranscribeRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    text = await ai_service.transcribe_audio(data.audioData, data.mimeType)
    return {"text": text}


@app.get("/api/health")
async def health():
    return {"status": "online", "service": "JARVIS AI OS"}
