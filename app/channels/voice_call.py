from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.agent.fitness_agent import run_agent
from app.agent.memory import get_or_create_user
from app.channels.capabilities import Channel
from app.db.session import AsyncSessionLocal

router = APIRouter()

_GATHER_TIMEOUT = 3
_VOICE = "Polly.Joanna"  # AWS Polly via Twilio — swap for ElevenLabs TTS if needed


@router.post("/incoming")
async def incoming_call(From: str = Form(...)):
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/channels/voice/respond",
        timeout=_GATHER_TIMEOUT,
        speech_timeout="auto",
    )
    gather.say("Hey! I'm Apex, your fitness coach. What's on your mind?", voice=_VOICE)
    response.append(gather)
    response.redirect("/channels/voice/incoming")
    return PlainTextResponse(str(response), media_type="application/xml")


@router.post("/respond")
async def call_respond(From: str = Form(...), SpeechResult: str = Form(default="")):
    if not SpeechResult:
        response = VoiceResponse()
        response.say("I didn't catch that — could you say it again?", voice=_VOICE)
        response.redirect("/channels/voice/incoming")
        return PlainTextResponse(str(response), media_type="application/xml")

    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, From)
        result = await run_agent(SpeechResult, user, Channel.VOICE_CALL, db)

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/channels/voice/respond",
        timeout=_GATHER_TIMEOUT,
        speech_timeout="auto",
    )
    gather.say(result.text, voice=_VOICE)
    response.append(gather)
    response.redirect("/channels/voice/incoming")
    return PlainTextResponse(str(response), media_type="application/xml")
