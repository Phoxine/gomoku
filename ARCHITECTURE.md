# Gomoku Architecture

Gomoku lets two people play a turn-based game in one browser. Django serves the board and the game API, and PostgreSQL stores games so players can resume them by ID.

## Code map

Arrows show the direction of calls or data access.

```text
Browser → Django API → GameApplicationService → GameRepository → Django ORM → PostgreSQL
                              │
                              └→ Game rules service
```

- **Web and routing.** Start at `src/config/urls.py` to find the page and API routes. The `game.html` template and `game.js` handle board rendering, player input, and restoring the last game ID.
- **HTTP interface.** `game_views.py` parses requests and maps service outcomes to HTTP responses. `game_dto.py` defines the request and response DTOs. The move endpoint passes a game ID and a `Move` to the application service, then converts the returned `GameState` to a response DTO.
- **Use cases.** `GameApplicationService` coordinates creating and loading games and submitting moves. It loads state through `GameRepository`, calls `apply_move` with that state and the move, and saves the returned state.
- **Game rules.** Find board and move validation, turn changes, and win and draw detection in `src/app/domain/game/service/game_service.py`. The `GameState` and `Move` types live in `state.py`. Search for `game_service_test.py` and `game_state_transition_test.py` for examples of the rules.
- **Persistence.** `GameRepository` translates between the domain state and Django model instances. The `Game` model and the game domain migrations own the storage constraints.
- **Runtime.** `src/config/settings.py` registers the game domain and configures PostgreSQL. `src/manage.py` is the management command entry point, and `src/config/` provides the WSGI and ASGI entry points.

## Architectural boundaries

- HTTP handlers translate between JSON and application service inputs and outputs. The repository owns ORM access and returns domain state to the application service. See the [API rules](.codex/rules/api.md) for DTO and API layer requirements.
- The game rules service and state types are independent of Django and PostgreSQL. The application service owns orchestration, including transactions, and the model can reuse the rules service for its empty-board default.
- Moves are applied to a 15×15 board. The rules service owns the conditions for valid moves, wins, draws, and completed games, so callers share the same transition rules.

## Cross-cutting concerns

- **Concurrent moves.** The application service holds a transaction while the repository locks the game row, the rules service computes the next state, and the repository saves it. The lock serializes moves for the same game.
- **HTTP security.** Django enforces CSRF checks on state-changing requests. Access to a game is currently based on knowing its ID and being able to reach the server. See the [security rules](.codex/rules/security.md) for input, credential, logging, and SQL requirements.
- **Development isolation.** Each worktree uses a separate Docker Compose project for Django and PostgreSQL. [Development setup](docs/development.md#development-setup)

## Detailed contracts

- [Game domain design](docs/domains/game/context-designs.md)
- [Game API](docs/domains/game/apis.md)
- [Database schema](docs/domains/game/db-schemas.md)
