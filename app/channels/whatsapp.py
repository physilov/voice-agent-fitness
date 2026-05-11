from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from app.agent.fitness_agent import run_agent
from app.agent.memory import get_or_create_user
from app.channels.capabilities import Channel
from app.db.session import AsyncSessionLocal

router = APIRouter()


@router.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
):
    phone_number = From.replace("whatsapp:", "")
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, phone_number)
        result = await run_agent(Body, user, Channel.WHATSAPP, db)

    twiml = MessagingResponse()
    twiml.message(result.text)
    return PlainTextResponse(str(twiml), media_type="application/xml")
