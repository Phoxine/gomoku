# API Rules

**Scope:** `src/app/api/**`

All APIs must comply with the following requirements:

- Use DTOs as request and response models. Convert domain results to response DTOs and never return domain entities or ORM models directly.
- Call application services for game operations. Do not import Django ORM models or access the database from the API layer.

See [Architectural boundaries](../../ARCHITECTURE.md#architectural-boundaries) for layer responsibilities and dependency direction.
