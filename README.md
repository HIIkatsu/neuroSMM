# NeuroSMM V2

**NeuroSMM V2** is a ground-up rewrite of the NeuroSMM platform — a Telegram bot + Mini App product for AI-powered social media content creation and publishing.

This repository is a **clean-slate V2 implementation**. It does not contain, port, or adapt any code from the previous version.

---

## What is NeuroSMM?

NeuroSMM helps content creators and social media managers:

- Generate AI text content for posts
- Generate AI images for posts
- Preview and edit content drafts
- Schedule and publish content automatically
- Manage a content plan across multiple channels

The product is delivered as a **Telegram bot** with an embedded **Mini App** (Web App) for richer interactions.

---

## V2 Goals

- Clean, modular, testable architecture
- FastAPI backend with clear service boundaries
- aiogram-based Telegram bot
- Separated text generation, image generation, and orchestration
- Strong validation and logging throughout
- No hallucination-heavy factual content by default
- Designed for phased, incremental delivery

---

## Repository Structure

```
app/
  core/            # Configuration, logging, base exceptions, shared utilities
  domain/          # Pure domain models and business rules (no I/O)
  services/        # Application-level service layer
  integrations/    # External service adapters (OpenAI, Telegram, storage, etc.)
  api/             # FastAPI application, routers, request/response schemas
  bot/             # aiogram bot handlers, FSM, middlewares
  miniapp/         # Mini App backend (if separate from main API)
  generation/
    text/          # Text generation service
    image/         # Image generation service
    orchestration/ # Content orchestration logic
docs/              # Architecture docs, rewrite spec, rules, and plan
tests/             # Test suite (mirrors app/ structure)
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/rewrite_spec.md](docs/rewrite_spec.md) | Product goals, user flows, V2 architecture principles |
| [docs/rewrite_rules.md](docs/rewrite_rules.md) | Hard rules for V2 development |
| [docs/pr_plan.md](docs/pr_plan.md) | 10-PR phased rewrite plan |
| [docs/architecture_note.md](docs/architecture_note.md) | Subsystem separation overview |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI |
| Bot | aiogram 3.x |
| Testing | pytest |
| Validation | Pydantic v2 |
| Async | asyncio / anyio |

---

## Status

🚧 **V2 is in active development.** See [docs/pr_plan.md](docs/pr_plan.md) for the phased delivery plan.

---

> **Note:** The previous NeuroSMM repository is treated as a product reference only. No legacy code, patterns, or adapters from the old codebase are used here.
