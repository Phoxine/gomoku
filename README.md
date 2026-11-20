# Gomoku

Gomoku is a web-based game under development. The intended first release supports two players taking turns on a 15×15 board, with each game saved in PostgreSQL. A player wins by placing five or more consecutive stones horizontally, vertically, or diagonally.

See the [architecture overview](ARCHITECTURE.md) for the request flow, component responsibilities, and technical contracts.

Browse the [documentation index](docs/index.md) for design and API details, or read the [local two-player specification](docs/product-specs/local-two-player-game.md) for supported gameplay and current limitations.

## Development setup

Install Docker and Docker Compose, then initialize and start the environment from the checkout:

```bash
bash scripts/init-worktree-env.sh
bash scripts/compose.sh up --build -d
```

Each worktree needs its own initialization, Compose project, and database volume. The initializer creates local environment files and a project name for the worktree; do not share or symlink those files between worktrees. Use `bash scripts/compose.sh` to run Compose commands for the current worktree. The database is accessible to the app on the private Compose network, without a host-published port. `bash scripts/compose.sh down` removes containers and the network while retaining the database volume.

### Python container image updates

The [app Dockerfile](docker/Dockerfile) and the [local documentation checker](scripts/check-docs.sh) each pin the `python:3.14-slim` image by digest. Keep the pins explicit so each entry point can run independently and its image version is visible in the file that uses it.

Update both pins in the same PR for routine image refreshes, including security updates. If an update applies to only one container, explain the reason in the PR. Rebuild the app and run the [worktree validation steps](.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Run `bash scripts/check-docs.sh` from the repository root to check Markdown and run the checker regression tests with the tooling image.

## Django management commands

After initializing and starting the isolated worktree environment as described in [Development setup](#development-setup), run:

```bash
bash scripts/compose.sh exec app uv run python manage.py check
bash scripts/compose.sh exec app uv run python manage.py migrate
```

The app container receives `DJANGO_SECRET_KEY` and `DEBUG` from its local environment and `DATABASE_URL` from Compose. `DEBUG` defaults to `False` and accepts `True` or `False`; the secret key and PostgreSQL URL are required. The base Compose configuration does not publish an app port. Configure an appropriate secret, allowed hosts, and deployment settings for any non-local deployment.

## Play locally

Initialize the isolated worktree environment following [Development setup](#development-setup). Set a distinct `APP_PORT` in the worktree's root `.env` and `DEBUG=True` in `src/.env`, then run:

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
