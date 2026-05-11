from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_whatsapp_number: str = ""

    # ExerciseDB (RapidAPI)
    exercisedb_api_key: str = ""
    exercisedb_base_url: str = "https://exercisedb.p.rapidapi.com"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # Deepgram
    deepgram_api_key: str = ""

    # App
    base_url: str = "http://localhost:8000"


settings = Settings()
