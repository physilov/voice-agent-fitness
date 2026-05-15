from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.session import init_db
from app.channels.whatsapp import router as whatsapp_router
from app.channels.voice_call import router as voice_router
from app.channels.web import router as web_router
from app.scheduler import load_reminders, start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    await load_reminders()
    yield
    stop_scheduler()


app = FastAPI(title="Voice Fitness Agent", lifespan=lifespan)

app.include_router(whatsapp_router, prefix="/channels/whatsapp", tags=["whatsapp"])
app.include_router(voice_router, prefix="/channels/voice", tags=["voice"])
app.include_router(web_router, prefix="/channels/web", tags=["web"])


@app.get("/health")
async def health():
    return {"status": "ok"}
