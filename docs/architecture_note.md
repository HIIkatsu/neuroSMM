# NeuroSMM V2 — Architecture Note

## Purpose

This note describes how V2 separates its major subsystems and why these boundaries exist.

---

## Subsystem Boundaries

### 1. Text Generation (`app/generation/text/`)

**Responsibility:** Given a topic, tone, and context, produce a text draft for a social media post.

**Interface:** `TextGenerationService.generate(prompt: TextPrompt) -> TextDraft`

**Dependencies:** OpenAI API adapter (injected). No DB access. No bot knowledge.

**Why isolated:** Text generation logic (prompt construction, retries, output parsing) changes independently of bot UX and publishing logic. It must be testable with a mocked LLM client.

---

### 2. Image Generation (`app/generation/image/`)

**Responsibility:** Given a prompt or context, produce one or more candidate images.

**Interface:** `ImageGenerationService.generate(prompt: ImagePrompt) -> list[GeneratedImage]`

**Dependencies:** Image AI adapter (OpenAI DALL-E or compatible). No DB. No bot.

**Why isolated:** Image generation may use a different provider or model than text generation. Keeping it separate allows independent substitution.

---

### 3. Content Orchestration (`app/generation/orchestration/`)

**Responsibility:** Coordinate text and image generation to produce a complete content draft. Decides when and how to call each generator, combines outputs, and persists the result via the DraftService.

**Interface:** `OrchestrationService.create_draft(request: DraftRequest) -> Draft`

**Dependencies:** TextGenerationService, ImageGenerationService, DraftService.

**Why isolated:** Orchestration logic (e.g., "generate text first, then infer image prompt from text") is distinct from the generation implementations themselves. It also owns retry and fallback decisions.

---

### 4. Bot Flows (`app/bot/`)

**Responsibility:** Handle all Telegram bot interactions — incoming messages, commands, inline buttons, FSM states, and Mini App launch.

**Interface:** aiogram Router handlers that call service layer methods via injected service instances.

**Dependencies:** Services (UserService, ProjectService, DraftService, OrchestrationService). No direct DB access. No direct OpenAI calls.

**Why isolated:** Bot handlers deal with Telegram-specific UX concerns (message formatting, button layouts, FSM state machine). Keeping them thin and service-delegating means bot behavior is fully controlled by the service layer, which is testable independently of Telegram.

---

### 5. Mini App Backend (`app/api/` + `app/miniapp/`)

**Responsibility:** Serve the REST API consumed by the Telegram Mini App frontend. Handle auth (Telegram initData validation), expose CRUD endpoints for projects, drafts, and content plans.

**Interface:** FastAPI routers with Pydantic-validated request/response models.

**Dependencies:** Same service layer as the bot. The service layer is shared — bot and API are two entry points to the same business logic.

**Why isolated:** The Mini App frontend has its own lifecycle, versioning, and deployment. Its backend needs to be independently testable via HTTP (TestClient) without spinning up the bot.

---

### 6. Mini App Frontend (`app/miniapp/frontend/` — future)

**Responsibility:** Telegram Web App UI (HTML/JS or TS/React). Provides the rich interface for content creation, draft editing, and content plan management.

**Interface:** Communicates with the Mini App Backend via REST API. Uses Telegram Web App SDK for auth and navigation.

**Why isolated:** Frontend has its own build toolchain, testing approach, and deployment. It is kept completely separate from Python backend code.

---

### 7. Scheduler / Autopost / Integrations (`app/services/scheduler_service.py` + `app/integrations/`)

**Responsibility:**
- `SchedulerService` — manages the content plan, persists scheduled posts, triggers publishing at the right time.
- Publishing adapters in `app/integrations/` — send actual posts to Telegram channels or other platforms.
- Background task runner — polls or uses APScheduler to fire publishing tasks.

**Interface:** `SchedulerService.schedule(draft_id, publish_at)` → persists; background runner calls `PublishingAdapter.publish(post)` at the right time.

**Dependencies:** DraftService, platform adapters (Telegram Bot API, etc.).

**Why isolated:** Publishing is the most failure-prone and externally coupled part of the system. Isolating it means retries, error handling, and platform-specific quirks are contained. It also allows future multi-channel support without changing the scheduler logic.

---

## Dependency Direction Summary

```
Bot handlers  ──► Services  ──► Domain models
API routers   ──► Services  ──► Domain models
                    │
                    └──► Integrations (DB, OpenAI, Telegram publisher)
Generation    ──► Services (DraftService) for persistence
Orchestration ──► Text Gen + Image Gen + DraftService
```

**Rule:** Dependencies always point inward (toward domain). The domain and services never depend on integrations or transport layers (bot, API). Integrations implement interfaces defined by the service layer.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Shared service layer between bot and API | Single source of truth for business logic |
| No business logic in bot handlers or API routers | Handlers/routers are thin transport adapters |
| Generation subsystems are separate from services | Generation providers may change independently |
| Domain models are I/O-free | Enables fast unit testing of all business rules |
| Async throughout | Required for Telegram bot and FastAPI performance |
| Pydantic v2 at all boundaries | Prevents unvalidated data from entering core logic |
