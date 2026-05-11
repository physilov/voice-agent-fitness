# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Vision

Voice-first fitness coaching agent accessible via **WhatsApp** and **phone calls**. Users interact entirely through natural conversation — asking for workout plans, logging activity, tracking progress, and receiving coaching — without opening an app.

## Core Technical Concepts

### Voice/Messaging Channels
- **WhatsApp**: Twilio WhatsApp API or WhatsApp Business API for text/voice messages
- **Phone calls**: Twilio Voice or similar (Vonage, Plivo) for inbound/outbound calls with speech-to-text and text-to-speech
- The agent must handle both synchronous (call) and asynchronous (WhatsApp message) interaction patterns

### AI Agent Layer
- Conversational AI powered by Claude (claude-sonnet or claude-opus) for fitness coaching logic
- Tool use / function calling for: logging workouts, querying progress, generating plans
- Session/memory management to maintain context across multi-turn conversations and across channels

### Fitness Domain
- Workout plan generation (user goals, fitness level, equipment)
- Exercise logging (sets, reps, weight, duration)
- Progress tracking (streaks, volume, personal records)
- Nutritional guidance if in scope

## Expected Stack (to be confirmed as code is added)

- **Runtime**: Node.js (TypeScript) or Python — TBD
- **Webhook server**: Express / FastAPI to receive Twilio webhooks
- **Database**: Persistent user state (workouts, preferences, history)
- **Claude API**: `@anthropic-ai/sdk` (Node) or `anthropic` (Python)
- **Twilio SDK**: For call and message handling

## Key Architectural Patterns to Follow

### Conversation State
Each user (identified by phone number) has a persistent conversation state. The agent must:
1. Load user context before each turn
2. Pass relevant history/memory to Claude
3. Persist updated state after each turn

### Webhook → Agent → Response Flow
```
Incoming message/call
  → Twilio webhook POST
    → Load user session
      → Run Claude agent with tools
        → Execute tool calls (DB reads/writes)
          → Return response text
            → Twilio sends reply
```

### Channel Abstraction
Keep channel-specific code (Twilio webhook parsing, TwiML generation) separate from the core agent logic so the fitness coaching brain is channel-agnostic.

## Development Commands

> Commands will be documented here once the project is initialized (package.json / pyproject.toml added).

## Environment Variables

Document required env vars here as they are introduced. Expected ones:
- `ANTHROPIC_API_KEY` — Claude API key
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` — Twilio credentials
- `TWILIO_PHONE_NUMBER` / `TWILIO_WHATSAPP_NUMBER`
- `DATABASE_URL` — connection string for user/workout storage
