# Development guide

## Development setup

Install Docker and Docker Compose, then initialize and start the environment from the checkout.

```bash
bash scripts/init-worktree-env.sh
bash scripts/compose.sh up --build -d
```

Each worktree needs its own initialization, Compose project, and database volume. The initializer creates local environment files and a project name for the worktree. Do not share or symlink those files between worktrees. Use `bash scripts/compose.sh` to run Compose commands for the current worktree. The database is accessible to the app on the private Compose network, without a host-published port. `bash scripts/compose.sh down` removes containers and the network while retaining the database volume.

## Run tests

With the worktree's app container running, run the Python test suite from the repository root.

```bash
bash scripts/compose.sh exec app uv run pytest
```

## Django management commands

After [starting the isolated worktree environment](#development-setup), use these commands to check Django configuration and apply migrations.

```bash
bash scripts/compose.sh exec app uv run python manage.py check
bash scripts/compose.sh exec app uv run python manage.py migrate
```

The app container receives `DJANGO_SECRET_KEY` and `DEBUG` from its local environment and `DATABASE_URL` from Compose. `DEBUG` defaults to `False` and accepts `True` or `False`; the secret key and PostgreSQL URL are required. The base Compose configuration does not publish an app port. Configure an appropriate secret, allowed hosts, and deployment settings for any non-local deployment.

## Play locally

Initialize the isolated worktree environment following [Development setup](#development-setup). Set a distinct `APP_PORT` in the worktree's root `.env` and `DEBUG=True` in `src/.env`.

An exported `APP_PORT` takes precedence over the value in the worktree's root `.env`. To use the port from `.env`, run `unset APP_PORT` before starting the web stack.

Start the web stack and apply migrations.

```bash
bash scripts/compose.sh -f compose.web.yaml up -d
bash scripts/compose.sh exec app uv run python manage.py migrate
```

Open `http://localhost:<APP_PORT>/`. The web override publishes the development server on the host's loopback address (`127.0.0.1`). The same browser restores its last game, and the game ID can be used to load a game manually. The interface supports two players taking turns on one device. See the [local two-player specification](product-specs/local-two-player-game.md) for gameplay and current limitations.

To stop the containers while retaining the database volume, run `bash scripts/compose.sh down`.

### Start the local server with one command

From the checkout, run the startup script.

```bash
bash scripts/start-local-server.sh
```

The script creates a local root `.env` with this checkout's Compose project name and a database password when one does not exist, then starts the web stack and applies migrations. It defaults to port `8000`. To use another port, follow the [port settings above](#play-locally). You can also specify a port when starting the server, for example with `APP_PORT=8766 bash scripts/start-local-server.sh`. The script refuses to create a new project when it detects the legacy `gomoku` database volume without its environment file, preserving that volume. Stop the server with `bash scripts/compose.sh down`.

## Python container image updates

The [app Dockerfile](../docker/Dockerfile) and the [local documentation checker](../scripts/check-docs.sh) each pin the `python:3.14-slim` image by digest. Keep the pins explicit so each entry point can run independently and its image version is visible in the file that uses it.

Update both pins in the same PR for routine image refreshes, including security updates. If an update applies to only one container, explain the reason in the PR. Rebuild the app and run the [worktree validation steps](../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Run `bash scripts/check-docs.sh` from the repository root to check Markdown and run the checker regression tests with the tooling image.

## Python coverage in pull requests

Open the GitHub Actions workflow run from the pull request's **Checks** tab and look for **Python line coverage** on the **Summary** page. For file and line details, download `python-coverage` from **Artifacts**. The archive contains `coverage.xml` for the commit tested by that run and is available for 14 days. It includes lines in `src/app` recorded during pytest and its Python subprocesses, including Django integration tests.

CI requires at least 90% overall Python line coverage, calculated from the exact line counts. When pytest passes and coverage falls below 90%, the quality check fails while the summary and XML remain available for diagnosis.
