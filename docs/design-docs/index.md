# Design Documents

Verification records which implementation and tests were checked against each document at commit `a9374b9`.

| Document | Status | Scope and evidence |
| --- | --- | --- |
| [Game domain design](../domains/game/context-designs.md) | **Verified** | Board rules, state transitions, transaction and locking behavior, and browser flow. [Rules service](../../src/app/domain/game/service/game_service.py), [state types](../../src/app/domain/game/state.py), [transition tests](../../src/tests/game_state_transition_test.py), [application service](../../src/app/domain/game/service/application_service.py), [repository](../../src/app/domain/game/repository/game_repository.py), [PostgreSQL integration tests](../../src/tests/game_application_service_test.py), [browser code](../../src/app/static/game/game.js) |
| [Game API](../domains/game/apis.md) | **Verified** | Routes, request validation, response fields and status codes, and CSRF handling. [URL routes](../../src/config/urls.py), [HTTP handlers](../../src/app/api/game_views.py), [DTOs](../../src/app/api/game_dto.py), [middleware settings](../../src/config/settings.py), [API integration tests](../../src/tests/game_api_test.py) |
| [Game database schema](../domains/game/db-schemas.md) | **Verified** | `games` fields, defaults, primary key, and PostgreSQL check constraints. [Game model](../../src/app/domain/game/model/game.py), [initial migration](../../src/app/domain/game/migrations/0001_initial.py), [board constraint](../../src/app/domain/game/model/board_constraint.py), [model integration tests](../../src/tests/game_model_test.py) |

## Shared principles

See [Core Beliefs](core-beliefs.md) for principles that apply across project tasks.
