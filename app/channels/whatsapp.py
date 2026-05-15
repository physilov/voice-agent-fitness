import httpx
from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from app.agent.fitness_agent import run_agent
from app.agent.memory import get_or_create_user
from app.channels.capabilities import Channel
from app.config import settings
from app.db.session import AsyncSessionLocal

router = APIRouter()


@router.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MediaUrl0: str | None = Form(None),
    MediaContentType0: str | None = Form(None),
):
    phone_number = From.replace("whatsapp:", "")

    image_data: bytes | None = None
    image_media_type: str | None = None
    if NumMedia > 0 and MediaUrl0:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    MediaUrl0,
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                    follow_redirects=True,
                )
                resp.raise_for_status()
                image_data = resp.content
                image_media_type = MediaContentType0 or "image/jpeg"
        except Exception:
            pass

    user_text = Body or ("" if image_data else "")

    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, phone_number)
        result = await run_agent(
            user_text, user, Channel.WHATSAPP, db,
            image_data=image_data,
            image_media_type=image_media_type,
        )

    twiml = MessagingResponse()
    twiml.message(result.text)
    return PlainTextResponse(str(twiml), media_type="application/xml")
