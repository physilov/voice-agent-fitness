# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Vision

Voice-first fitness coaching agent (named **Apex**) accessible via **WhatsApp**, **phone calls**, **web**, and **mobile app**. Users interact through natural conversation — asking for workout plans, logging activity, tracking progress, and receiving full coaching including nutrition — without opening a dedicated app.

Web and mobile channels additionally support **GenUI**: the agent emits structured UI component specs that the frontend renders dynamically (exercise animations, progress charts, PR celebrations, etc.).

## Commands

```bash
# Install dependencies
uv sync

# Run the development server
uv run uvicorn app.main:app --reload --port 8000

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_agent.py -v

# Lint / format
uv run ruff check .
uv run ruff format .

# Database migrations
uv run alembic upgrade head                              # apply all
uv run alembic revision --autogenerate -m "description"  # new migration
uv run alembic downgrade -1                              # roll back one
```

Copy `.env.example` → `.env` and fill in at minimum `ANTHROPIC_API_KEY` and `DATABASE_URL` before first run.

## Architecture

### Channel → Agent Flow

Every channel normalizes input to `{user, text, channel}` before hitting the agent:

```
[WhatsApp]  [Phone Call]  [Web/WS]  [Mobile App]
     ↓            ↓           ↓           ↓
  app/channels/whatsapp  voice_call  web  (app uses /web/chat)
                          ↓
              app/agent/fitness_agent.py   ← Claude tool-use loop
                  ├── tools.py             ← all DB-backed tool handlers
                  ├── memory.py            ← load history / save turn / compress
                  └── prompts.py           ← system prompt from user profile
                          ↓
              CompoundResponse { text, ui_components, actions }
                          ↓
     ┌──────────────────────────────────────┐
  Text-only channels                  Rich channels (web/app)
  (WhatsApp, voice)                   render UIComponents via GenUI
```

### CompoundResponse and GenUI (`app/agent/response_schema.py`)

The agent always returns a `CompoundResponse`. The `text` field goes to every channel; `ui_components` is only rendered by channels where `CAPABILITIES[channel].can_render_ui == True` (see `app/channels/capabilities.py`).

UI component types (emitted by tool handlers in `tools.py`):

| `type` | Emitted by tool |
|---|---|
| `exercise_animation` | `show_exercise_animation` |
| `workout_plan_card` | `get_current_plan` |
| `progress_chart` | `get_progress_summary` |
| `nutrition_breakdown` | `log_nutrition` |
| `pr_celebration` | `check_personal_record` |

### Agent Tool Loop (`app/agent/fitness_agent.py`)

Standard Claude tool-use loop: send messages → if `stop_reason == "tool_use"`, dispatch to `handle_tool_call()` in `tools.py` → append tool results → repeat until `end_turn`. All DB writes happen inside tool handlers; the agent loop itself never writes to the DB.

### Memory (`app/agent/memory.py`)

Two layers of persistence per user:
1. **Recent messages** — last 20 turns kept verbatim, prepended to every Claude call.
2. **Memory summary** (`users.memory_summary`) — when total message count exceeds 40, a Claude call summarizes the full history and old messages are pruned. This bounds context window growth for long-term users.

### Voice Call Flow (`app/channels/voice_call.py`)

Twilio Voice webhooks with `<Gather input="speech">`:
1. `POST /channels/voice/incoming` — play greeting, open `<Gather>`
2. `POST /channels/voice/respond` — receive `SpeechResult` → run agent → TTS via `<Say>` → loop back to `<Gather>`

The voice channel sets `Channel.VOICE_CALL` so the system prompt appends a brevity constraint (≤2 sentences per response).

### Exercise Animations (`app/services/exercisedb.py`)

Queries the ExerciseDB RapidAPI (1,300+ exercises with GIF animations) and caches results in the `exercise_cache` table. The `show_exercise_animation` tool does a normalized name lookup against the cache first, then falls back to the API. The frontend receives `gif_url` + `coaching_cues` and renders them as an overlay.

### Form Analysis (`app/services/form_analysis.py`)

The client runs MediaPipe Pose and streams landmark keypoints via WebSocket. `analyze_frame(exercise, landmarks_raw)` compares key joint angles against reference ranges and returns real-time cues. The agent only receives the post-session summary — not the raw stream — and responds with coaching notes.

## Key Files

| File | Purpose |
|---|---|
| `app/agent/fitness_agent.py` | Claude tool-use loop — entry point for all agent calls |
| `app/agent/tools.py` | All 9 tool definitions + DB-backed handlers |
| `app/agent/memory.py` | Conversation history load/save and rolling summarization |
| `app/agent/prompts.py` | System prompt template populated from `User` model |
| `app/db/models.py` | All SQLAlchemy models (User, WorkoutPlan, WorkoutLog, PersonalRecord, NutritionLog, ConversationMessage, ExerciseCache) |
| `app/channels/capabilities.py` | Per-channel feature flags — controls whether UI components are sent |
| `app/services/exercisedb.py` | ExerciseDB API client with DB caching |

## Environment Variables

See `.env.example` for the full list. Required:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API |
| `DATABASE_URL` | PostgreSQL — `postgresql+asyncpg://...` |
| `REDIS_URL` | Voice call session state |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | WhatsApp + voice channels |
| `TWILIO_PHONE_NUMBER` / `TWILIO_WHATSAPP_NUMBER` | Twilio numbers |
| `EXERCISEDB_API_KEY` | RapidAPI key for exercise animations |
| `ELEVENLABS_API_KEY` | TTS for phone calls |
