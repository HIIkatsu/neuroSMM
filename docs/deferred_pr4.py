"""
Deferred Architectural Decisions — PR4 (Database Layer)
=======================================================

This module documents intentional scope decisions made during PR4.
It is NOT runnable code — it exists solely for traceability.

1. GenerationRequest / GenerationResult — NOT persisted
-------------------------------------------------------
These are value objects (no identity, no surrogate ID).  They represent
ephemeral request/response pairs for AI generation calls.  Persisting them
would require:

* A new table with a foreign key to Draft.
* Deciding on retention policy (how long to keep generation history).
* Modelling generation *sessions* (multiple attempts per draft).

None of this is needed for the current PR scope (persistence of core
entities).  Generation history can be added in PR7/PR8 when the
text/image generation services are implemented and the actual data
flow is concrete.

2. Project vs Channel separation
---------------------------------
The current domain model treats ``Project`` as a 1:1 wrapper around a
publishing channel.  A future design might separate the "project"
(campaign / workspace) from the "channel" (platform-specific endpoint)
to support multi-channel publishing from a single project.

This is **not** a persistence-layer concern — it would be a domain
redesign.  The current schema (``projects`` table with
``platform_channel_id``) is forward-compatible: splitting into two
tables later requires only a new migration and mapper update.

3. image_url modelling
-----------------------
``Draft.image_url`` is currently a plain string (URL or storage key).
A richer media model (storage backend, mime type, thumbnails, etc.)
may be needed once image generation is integrated.

This can be handled by:
* Adding a ``media`` table with a FK from ``drafts`` (PR8 scope).
* Keeping the existing ``image_url`` column as a lightweight fallback.

No schema change is needed now.

4. SQLite for tests, PostgreSQL for production
----------------------------------------------
All integration tests use in-memory SQLite via ``aiosqlite``.  The
``DateTime(timezone=True)`` columns lose tzinfo in SQLite, so the
mappers include an ``ensure_utc()`` normalizer that re-attaches UTC
on read.  This is harmless on PostgreSQL (which preserves tz natively)
and ensures domain models always receive tz-aware datetimes.
"""
