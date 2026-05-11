from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.fitness_agent import run_agent
from app.agent.memory import get_or_create_user
from app.agent.response_schema import CompoundResponse
from app.channels.capabilities import Channel
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter()


class ChatRequest(BaseModel):
    phone_number: str
    message: str


@router.post("/chat", response_model=CompoundResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    user = await get_or_create_user(db, request.phone_number)
    return await run_agent(request.message, user, Channel.WEB, db)


@router.websocket("/ws/{phone_number}")
async def websocket_chat(websocket: WebSocket, phone_number: str):
    await websocket.accept()
    try:
        async with AsyncSessionLocal() as db:
            user = await get_or_create_user(db, phone_number)
            while True:
                text = await websocket.receive_text()
                result = await run_agent(text, user, Channel.WEB, db)
                await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        pass
