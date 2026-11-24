# Gomoku

Gomoku is a web game for two players sharing one device. Take turns placing stones on a 15×15 board. The first player to line up five or more stones horizontally, vertically, or diagonally wins. See the [local two-player specification](docs/product-specs/local-two-player-game.md) for gameplay and current limitations.

## Quick start

Install Docker and Docker Compose, then run this command from the repository root.

```bash
bash scripts/start-local-server.sh
```

Open the URL printed by the script. The default is http://localhost:8000/.

Use this command to stop the server and keep your saved games.

```bash
bash scripts/compose.sh down
```

## Documentation

- [Development guide](docs/development.md) for custom ports, contributor setup, testing, and maintenance.
- [Documentation index](docs/index.md) for architecture, game rules, API contracts, and data storage.
