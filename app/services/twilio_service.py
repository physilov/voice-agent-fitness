from twilio.rest import Client

from app.config import settings

_client: Client | None = None


def get_twilio_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _client


async def send_whatsapp_message(to: str, body: str):
    get_twilio_client().messages.create(
        from_=settings.twilio_whatsapp_number,
        to=f"whatsapp:{to}",
        body=body,
    )


async def initiate_outbound_call(to: str, callback_url: str):
    """Initiate a proactive outbound call, e.g. for a scheduled check-in."""
    get_twilio_client().calls.create(
        from_=settings.twilio_phone_number,
        to=to,
        url=callback_url,
    )
