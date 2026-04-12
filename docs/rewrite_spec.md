# NeuroSMM V2 — Rewrite Specification

## 1. Product Goals

NeuroSMM V2 is a Telegram-native content creation and publishing tool for social media managers and creators. The product delivers:

- **AI-assisted content creation** — text and image generation for social media posts
- **Content drafting and preview** — users see and edit output before publishing
- **Scheduling and autopublishing** — content plan with automated posting
- **Multi-channel orientation** — designed to support multiple social platforms (Telegram, VK, etc.)
- **Clean UX** — delivered through a Telegram bot and an embedded Mini App (Telegram Web App)

Non-goals for V2:
- Factual research / news generation
- SEO article creation
- Platform beyond Telegram entry point (in early phases)

---

## 2. Core User Flows

### 2.1 New Post Creation

1. User opens the bot or Mini App
2. User selects a channel / project
3. User provides a topic, tone, and optional reference
4. System generates a text draft (AI)
5. User reviews and edits the draft in the Mini App
6. User optionally generates an accompanying image
7. User approves the final post
8. User either publishes immediately or schedules it

### 2.2 Content Plan / Scheduler

1. User opens the content plan section in Mini App
2. User sees a calendar-style view of scheduled posts
3. User can create, reschedule, or delete planned posts
4. At the scheduled time, the system auto-publishes via the integration layer

### 2.3 Image Generation

1. User triggers image generation from a draft context or standalone
2. User provides a prompt or lets the system infer one from the text draft
3. System generates image options (1–4)
4. User selects or regenerates
5. Selected image is attached to the draft

### 2.4 Onboarding

1. User starts the bot (`/start`)
2. Bot introduces features briefly
3. User is invited to open the Mini App or use bot commands directly
4. User creates their first project / channel

---

## 3. Mandatory Features for V2

| Feature | Priority |
|---|---|
| Telegram bot core (start, menu, callbacks) | P0 |
| Mini App shell (FastAPI backend, Telegram Web App frontend stub) | P0 |
| User identity and session management | P0 |
| Project / channel management | P1 |
| AI text generation (OpenAI or compatible) | P1 |
| Content draft CRUD | P1 |
| AI image generation | P2 |
| Content plan / scheduler | P2 |
| Publishing integration (Telegram channel posting) | P2 |
| Notification / status feedback to user | P2 |

---

## 4. Features to Simplify or Drop in V2

| Feature | Decision |
|---|---|
| Legacy analytics dashboards | Drop — rebuild fresh if needed later |
| Complex legacy prompt chains | Simplify — use clean prompt templates |
| Old FSM spaghetti in bot | Drop — rebuild with aiogram 3.x FSM properly |
| Hardcoded channel configs | Drop — dynamic project/channel model |
| Any legacy API compatibility shims | Drop entirely |
| Fake "demo" content seeding | Drop |

---

## 5. V2 Architecture Principles

1. **Domain isolation** — Domain models and business rules live in `app/domain` and have no I/O dependencies.
2. **Service layer** — All business logic is in `app/services`. Services depend on domain and abstract interfaces (ports), not on concrete integrations.
3. **Integration adapters** — All external I/O (OpenAI, Telegram API, storage, DB) lives in `app/integrations` and implements interfaces defined in `app/services` or `app/domain`.
4. **API layer** — FastAPI routers in `app/api` are thin: they validate input, call services, return output. No business logic in routers.
5. **Bot layer** — aiogram handlers in `app/bot` are thin: they parse Telegram events and delegate to services. No business logic in handlers.
6. **Generation subsystems** — Text generation, image generation, and orchestration are separate modules with clear interfaces between them.
7. **Testability by design** — Core services and domain logic must be unit-testable without real external connections.
8. **Explicit over magic** — No hidden global state, no heavy DI containers, no metaclass magic. Dependencies are injected explicitly.
9. **Async throughout** — All I/O is async (asyncio). No blocking I/O in the request path.
10. **Validation at boundaries** — All external input (API, bot, integrations) is validated with Pydantic v2 before entering the service layer.

---

## 6. High-Level Subsystems

```
┌─────────────────────────────────────────────────────┐
│                   Telegram Bot                       │
│  aiogram handlers → service calls → bot responses   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   FastAPI Backend                    │
│  API routers → services → domain → integrations     │
│  Also serves Mini App backend endpoints             │
└──────┬───────────────┬──────────────────────────────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────────────────────┐
│  Generation  │  │         Core Services               │
│  subsystem   │  │  - UserService                     │
│  - text gen  │  │  - ProjectService                  │
│  - image gen │  │  - DraftService                    │
│  - orchestr. │  │  - SchedulerService                │
└──────┬───────┘  └─────┬──────────────────────────────┘
       │                │
┌──────▼────────────────▼──────────────────────────────┐
│                  Integrations Layer                   │
│  - OpenAI adapter                                    │
│  - Telegram publishing adapter                       │
│  - Database adapter (async SQLAlchemy / other)       │
│  - Storage adapter (files / S3-compatible)           │
└──────────────────────────────────────────────────────┘
```

---

## 7. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| API framework | FastAPI |
| Telegram bot | aiogram 3.x |
| Data validation | Pydantic v2 |
| Database ORM | SQLAlchemy (async) — to be decided in DB PR |
| Testing | pytest + pytest-asyncio |
| Task scheduling | APScheduler or Celery — to be decided in scheduler PR |
| Text AI | OpenAI API (GPT-4o or compatible) |
| Image AI | OpenAI DALL-E or compatible |
