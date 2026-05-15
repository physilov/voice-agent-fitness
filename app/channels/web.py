from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.fitness_agent import run_agent
from app.agent.memory import get_or_create_user
from app.agent.response_schema import CompoundResponse
from app.channels.capabilities import Channel
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter()


@router.post("/chat", response_model=CompoundResponse)
async def chat(
    phone_number: str = Form(...),
    message: str = Form(""),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    user = await get_or_create_user(db, phone_number)

    image_data: bytes | None = None
    image_media_type: str | None = None
    if image and image.filename:
        image_data = await image.read()
        image_media_type = image.content_type or "image/jpeg"

    return await run_agent(message, user, Channel.WEB, db, image_data=image_data, image_media_type=image_media_type)


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
