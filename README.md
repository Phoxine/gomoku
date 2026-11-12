# Gomoku

Gomoku is a web-based game under development. The intended first release supports two players taking turns on a 15×15 board, with each game saved in PostgreSQL. A player wins by placing five or more consecutive stones horizontally, vertically, or diagonally.

## Design

- **Game rules:** The framework-independent [game service](src/app/domain/game/service/game_service.py) validates moves and applies state transitions, including alternating turns, wins, draws, and finished-game rejection.
- **Persistence:** The Django [game model](src/app/domain/game/model/game.py) and its initial migration define game state and database constraints. The [repository](src/app/domain/game/repository/game_repository.py) and [application service](src/app/domain/game/service/application_service.py) create, retrieve, and update games; move updates use transactions and row locks to handle concurrency.
- **Architecture:** API handlers are intended to call domain services, with database access through domain repositories. Game rules remain independent of Django and the database.
- **Development:** Python 3.14, Django, and PostgreSQL run in isolated Docker Compose environments for each worktree. See the [worktree workflow](docs/codex/workflows/multi-session-worktrees.md).

The [game domain design](docs/domains/game/context-designs.md) and [database schema](docs/domains/game/db-schemas.md) describe the implemented rules and data model.

## Not yet implemented

- Django project configuration and game APIs for creating games, retrieving state, and submitting moves.
- A playable web interface with a board, turn and result indicators, and game state restoration.
- Account management, matchmaking, real-time multiplayer updates, and spectators.
