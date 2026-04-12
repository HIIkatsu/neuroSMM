# NeuroSMM V2 — Phased PR Plan

This document defines the delivery sequence for V2. Each PR has a strict scope.  
PRs must be implemented in order unless explicitly noted as parallelizable.

---

## PR 01 — V2 Foundation & Repository Skeleton ✅

**Status:** This PR  
**Scope:**
- README.md
- docs/ (rewrite_spec, rewrite_rules, pr_plan, architecture_note)
- Repository directory skeleton
- .gitignore, pyproject.toml, minimal Python scaffolding
- Empty package `__init__.py` files
- Minimal test scaffold

**Not included:** Any runtime logic, database, or integration code.

---

## PR 02 — Core Layer: Config, Logging, Base Exceptions

**Scope:**
- `app/core/config.py` — Settings via pydantic-settings (env-based)
- `app/core/logging.py` — Structured logging setup
- `app/core/exceptions.py` — Base exception hierarchy for V2
- `app/core/constants.py` — Shared constants
- Unit tests for config loading

**Not included:** Database, API, bot.

---

## PR 03 — Domain Models

**Scope:**
- `app/domain/user.py` — User entity
- `app/domain/project.py` — Project / channel entity
- `app/domain/draft.py` — Content draft entity
- `app/domain/schedule.py` — Scheduled post entity
- `app/domain/enums.py` — Shared enums (PostStatus, ContentType, etc.)
- Full unit tests for domain model validation and business rules

**Not included:** Database persistence, services, API.

**Constraint:** Domain models must have zero I/O dependencies. Pure Python + Pydantic only.

---

## PR 04 — Database Layer

**Scope:**
- Async SQLAlchemy setup
- `app/integrations/db/` — Session factory, base model
- DB models for User, Project, Draft, ScheduledPost
- Alembic migration scaffold
- Repository interfaces in `app/services/` (abstract base classes)
- Concrete repository implementations in `app/integrations/db/repositories/`
- Integration tests for repositories (using SQLite in-memory for CI)

**Not included:** API endpoints, bot handlers, generation.

---

## PR 05 — FastAPI Application Shell + User/Project API

**Scope:**
- FastAPI application factory (`app/api/app.py`)
- Health check endpoint
- Auth middleware skeleton (Telegram init data validation)
- `app/api/routers/users.py` — User registration / profile endpoints
- `app/api/routers/projects.py` — Project CRUD endpoints
- `app/services/user_service.py`
- `app/services/project_service.py`
- Tests for API endpoints (using TestClient + in-memory DB)

**Not included:** Draft API, generation, bot, scheduling.

---

## PR 06 — Draft Management API

**Scope:**
- `app/domain/draft.py` refinements
- `app/api/routers/drafts.py` — Draft CRUD (create, read, update, delete, list)
- `app/services/draft_service.py`
- Draft state transitions (DRAFT → READY → PUBLISHED)
- Tests for draft service and API

**Not included:** Generation, scheduling, publishing.

---

## PR 07 — Text Generation Service

**Scope:**
- `app/generation/text/service.py` — TextGenerationService interface + OpenAI implementation
- `app/generation/text/prompts.py` — Clean prompt templates (no legacy prompts)
- `app/integrations/openai/text_client.py` — Async OpenAI client adapter
- Integration with DraftService (generate → populate draft)
- API endpoint: `POST /drafts/{id}/generate-text`
- Unit tests with mocked OpenAI client

**Not included:** Image generation, bot, scheduling.

---

## PR 08 — Image Generation Service

**Scope:**
- `app/generation/image/service.py` — ImageGenerationService interface + implementation
- `app/integrations/openai/image_client.py` — Async image generation adapter
- `app/generation/orchestration/` — Orchestration logic to link text + image for a draft
- API endpoint: `POST /drafts/{id}/generate-image`
- Unit tests with mocked image client

**Not included:** Bot, scheduling, publishing.

---

## PR 09 — Telegram Bot Core

**Scope:**
- aiogram 3.x application setup (`app/bot/main.py`)
- Bot middleware: logging, user resolution
- Handlers: `/start`, main menu, basic navigation
- Mini App launch button / WebApp URL integration
- FSM scaffold for content creation flow (states only, no full generation flow yet)
- Bot calls existing API services (not direct DB access)

**Not included:** Full publishing flow, scheduler.

---

## PR 10 — Scheduler & Publishing Integration

**Scope:**
- `app/services/scheduler_service.py` — Schedule management
- `app/integrations/telegram/publisher.py` — Telegram channel posting adapter
- Background task runner (APScheduler or equivalent)
- API endpoints for content plan (list, create, update, delete scheduled posts)
- Bot command / Mini App interaction to schedule posts
- End-to-end test: create draft → schedule → publish (mocked Telegram)

**Not included:** Analytics, advanced multi-channel support.

---

## Future PRs (beyond initial 10)

- PR 11 — Mini App frontend skeleton (Telegram Web App HTML/JS/TS)
- PR 12 — Multi-channel publishing (VK or other platforms)
- PR 13 — Analytics and usage tracking
- PR 14 — Advanced content plan UI in Mini App
- PR 15 — Production hardening (rate limiting, error monitoring, deployment config)

---

## Notes

- PRs 05–10 may have some parallelism once PR 04 is merged.
- Each PR must reference this plan in its description.
- Deviations from this plan must be documented as an update to this file.
