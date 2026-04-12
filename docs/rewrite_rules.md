# NeuroSMM V2 — Rewrite Rules

These rules are **mandatory** for all contributors and PRs in this repository.  
They exist to prevent V2 from inheriting the architectural problems of the previous version.

---

## Hard Rules

### 1. No Legacy Code Reuse

- No file, function, class, or snippet from the previous NeuroSMM repository may be copied, ported, adapted, or wrapped into V2.
- This applies to prompt strings, utility helpers, FSM state definitions, DB schemas, and configuration patterns.
- The old repository may only be read as a **product reference** to understand what the product does, not how it was implemented.

### 2. No Legacy Wrappers

- Do not create "compatibility layers" or "migration adapters" that bridge old and new code.
- If a piece of logic is needed, rewrite it from scratch to meet V2 architecture standards.

### 3. No Mixed Architecture

- V2 architecture must be internally consistent at all times.
- Do not mix old patterns (e.g., synchronous Flask-style handlers) with V2 patterns.
- Do not introduce global mutable state, monolithic handlers, or ad-hoc configuration patterns.

### 4. Old Repository is Reference-Only

- Reading the old codebase to understand product behavior is allowed.
- Extracting, copying, or adapting any code from the old codebase is forbidden.
- PRs that contain adapted or ported legacy code will be rejected.

### 5. Phased PR Implementation Only

- Features must be delivered in focused, scoped PRs that follow the plan in `docs/pr_plan.md`.
- No PR may implement multiple unrelated phases at once.
- The sequence in `docs/pr_plan.md` exists for a reason — respect it.

### 6. Every PR Must Have a Strict Scope

- Each PR description must state:
  - What is being built
  - What is explicitly **not** included
  - Which `pr_plan.md` phase it corresponds to
- PRs with unclear or unbounded scope will be rejected.

### 7. Incomplete Work Must Be Stated Explicitly

- If a PR delivers partial functionality, it must say so in the PR description.
- Placeholder code (empty `__init__.py`, stub classes, TODO comments) is acceptable when clearly marked.
- Fake completeness — stub code that looks like a finished feature but does nothing real — is not allowed.

### 8. No Fake Integrations

- Do not add mock API clients, dummy OpenAI wrappers, or fake publishing adapters that simulate real behavior without actually connecting.
- Real integration skeletons with clear TODOs are fine; fake "working" integrations are not.

### 9. Test Coverage for Service Layer

- Every service in `app/services` must have corresponding unit tests in `tests/services`.
- Tests must be runnable without real external dependencies (use dependency injection and interfaces).

### 10. Validation at All Boundaries

- All external input entering the system (API requests, bot messages, integration responses) must be validated with Pydantic v2 before being processed.
- No raw dicts or unvalidated data may pass into the domain or service layer.

---

## Rule Enforcement

- These rules are enforced by code review.
- PRs that violate any rule must be updated before merging.
- If a rule needs to be changed, propose a docs update before changing the implementation.
