import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import async_session
from ..dependencies import get_db, get_ai_service
from ..schemas.chat import ChatCreate, ChatResponse, MessageResponse, StreamRequest
from ..services.chat import ChatService
from ..services.ai import AIService
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(data: ChatCreate, db: AsyncSession = Depends(get_db)):
    return await ChatService.create_chat(db, data.project_id, data.title)

@router.get("/{project_id}", response_model=List[ChatResponse])
async def get_chats(project_id: str, db: AsyncSession = Depends(get_db)):
    return await ChatService.get_chats(db, project_id)

@router.get("/chat/{chat_id}", response_model=ChatResponse)
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    chat = await ChatService.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    success = await ChatService.delete_chat(db, chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return None

@router.get("/chat/{chat_id}/history", response_model=List[MessageResponse])
async def get_chat_history(chat_id: str, db: AsyncSession = Depends(get_db)):
    chat = await ChatService.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat.messages

@router.post("/stream")
async def stream_chat(
    data: StreamRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    # Retrieve history and save user prompt in a separate connection to avoid generator locking
    async with async_session() as db:
        chat = await ChatService.get_chat(db, data.chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Format history context
        history = [{"role": m.role, "content": m.content} for m in chat.messages]
        
        # Save user message
        await ChatService.add_message(db, data.chat_id, "user", data.message)
        await db.commit()

    async def event_generator():
        accumulated_text = ""
        latency = 0.0
        token_count = 0
        model_used = data.model or "gemini-3.1-flash-lite"
        
        try:
            async for chunk in ai_service.stream_chat(
                message=data.message,
                history=history,
                system_instruction=data.systemInstruction or "You are JARVIS, an advanced AI Operating System. Answer elegantly, with a technical, refined, and helpful persona.",
                model=model_used,
                use_search=data.useSearch or False
            ):
                if "error" in chunk:
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                    return
                
                if chunk.get("done"):
                    latency = chunk.get("latency", 0.0)
                    token_count = chunk.get("token_count", 0)
                    model_used = chunk.get("model_used", model_used)
                    break
                
                text = chunk.get("text", "")
                accumulated_text += text
                yield f"data: {json.dumps({'text': text, 'searchChunks': chunk.get('searchChunks', [])})}\n\n"
            
            # Save Assistant response in db
            async with async_session() as db:
                await ChatService.add_message(
                    db,
                    chat_id=data.chat_id,
                    role="model",
                    content=accumulated_text,
                    token_count=token_count,
                    latency=latency
                )
                
                # Auto-rename if title remains default generic string
                chat_obj = await ChatService.get_chat(db, data.chat_id)
                if chat_obj and chat_obj.title in ["New Chat", "New Chat Session", "New Thread"]:
                    # Create generic short title from prompt first few words
                    words = data.message.split()
                    short_title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
                    await ChatService.update_chat_title(db, data.chat_id, short_title)
                    
                await db.commit()
                
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
