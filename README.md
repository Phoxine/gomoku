# Gomoku

Gomoku is a web-based game under development. The intended first release supports two players taking turns on a 15×15 board, with each game saved in PostgreSQL. A player wins by placing five or more consecutive stones horizontally, vertically, or diagonally.

## Design

- **Game rules:** The framework-independent [game service](src/app/domain/game/service/game_service.py) validates moves and applies state transitions, including alternating turns, wins, draws, and finished-game rejection.
- **Persistence:** The Django [game model](src/app/domain/game/model/game.py) and its initial migration define game state and database constraints. The [repository](src/app/domain/game/repository/game_repository.py) and [application service](src/app/domain/game/service/application_service.py) create, retrieve, and update games; move updates use transactions and row locks to handle concurrency.
- **Web interface:** The browser interface provides a 15×15 board, current turn and game result, and restores the last game on the same browser. Players can also enter a game ID to load it.
- **API:** The [game API](docs/domains/game/apis.md) creates and retrieves games and submits moves through the application service. Game rules remain independent of Django and the database.
- **Django project:** The [project configuration](src/config/settings.py) registers the game domain and connects to PostgreSQL. Management commands use `src/manage.py`; WSGI and ASGI entry points are provided.
- **Development:** Python 3.14, Django, and PostgreSQL run in isolated Docker Compose environments for each worktree. See the [worktree workflow](docs/codex/workflows/multi-session-worktrees.md).

The [game domain design](docs/domains/game/context-designs.md) and [database schema](docs/domains/game/db-schemas.md) describe the implemented rules and data model.

## Not yet implemented

- Account management, matchmaking, real-time multiplayer updates, and spectators.

## Django management commands

After initializing and starting the isolated worktree environment as described in the [worktree workflow](docs/codex/workflows/multi-session-worktrees.md), run:

```bash
bash scripts/compose.sh exec app uv run python manage.py check
bash scripts/compose.sh exec app uv run python manage.py migrate
```

The app container receives `DJANGO_SECRET_KEY` and `DEBUG` from its local environment and `DATABASE_URL` from Compose. `DEBUG` defaults to `False` and accepts `True` or `False`; the secret key and PostgreSQL URL are required. The base Compose configuration does not publish an app port. Configure an appropriate secret, allowed hosts, and deployment settings for any non-local deployment.

## Play locally

Initialize the isolated worktree environment following the [worktree workflow](docs/codex/workflows/multi-session-worktrees.md). Set a distinct `APP_PORT` in the worktree's root `.env` and `DEBUG=True` in `src/.env`, then run:

```bash
bash scripts/compose.sh -f compose.web.yaml up -d
bash scripts/compose.sh exec app uv run python manage.py migrate
```

Open `http://localhost:<APP_PORT>/`. The web override binds only to `127.0.0.1` and uses Django's development server; it is intended for local development only. The same browser restores its last game, and the game ID can be used to load a game manually. The interface is for two players taking turns on one device; accounts, authorization, and real-time updates are not implemented.

To stop the containers while retaining the database volume, run `bash scripts/compose.sh down`.

### Start the local server with one command

On a single checkout, run:

```bash
bash scripts/start-local-server.sh
```

The script creates a local root `.env` with this checkout's Compose project name and a database password when one does not exist, then starts the web stack and applies migrations. It defaults to port `8000`; set `APP_PORT` in the root `.env` to use another port. It refuses to create a new project when it detects the legacy `gomoku` database volume without its environment file, preserving that volume. Stop the server with `bash scripts/compose.sh down`.
