# Gomoku

Gomoku is a web-based game under development. The intended first release supports two players taking turns on a 15×15 board, with each game saved in PostgreSQL. A player wins by placing five or more consecutive stones horizontally, vertically, or diagonally.

## Design

- **Game rules:** The framework-independent [game service](src/app/domain/game/service/game_service.py) validates moves and applies state transitions, including alternating turns, wins, draws, and finished-game rejection.
- **Persistence:** The Django [game model](src/app/domain/game/model/game.py) and its initial migration define game state and database constraints. The [repository](src/app/domain/game/repository/game_repository.py) and [application service](src/app/domain/game/service/application_service.py) create, retrieve, and update games; move updates use transactions and row locks to handle concurrency.
- **API:** The [game API](docs/domains/game/apis.md) creates and retrieves games and submits moves through the application service. Game rules remain independent of Django and the database.
- **Django project:** The [project configuration](src/config/settings.py) registers the game domain and connects to PostgreSQL. Management commands use `src/manage.py`; WSGI and ASGI entry points are provided.
- **Development:** Python 3.14, Django, and PostgreSQL run in isolated Docker Compose environments for each worktree. See the [worktree workflow](docs/codex/workflows/multi-session-worktrees.md).

The [game domain design](docs/domains/game/context-designs.md) and [database schema](docs/domains/game/db-schemas.md) describe the implemented rules and data model.

## Not yet implemented

- A playable web interface with a board, turn and result indicators, and game state restoration.
- Account management, matchmaking, real-time multiplayer updates, and spectators.

## Django management commands

After initializing and starting the isolated worktree environment as described in the [worktree workflow](docs/codex/workflows/multi-session-worktrees.md), run:

```bash
bash scripts/compose.sh exec app uv run python manage.py check
bash scripts/compose.sh exec app uv run python manage.py migrate
```

The app container receives `DJANGO_SECRET_KEY` and `DEBUG` from its local environment and `DATABASE_URL` from Compose. `DEBUG` defaults to `False` and accepts `True` or `False`; the secret key and PostgreSQL URL are required. The game API routes are available inside the app container; Compose does not publish an app port. Configure an appropriate secret, allowed hosts, and deployment settings for any non-local deployment.
