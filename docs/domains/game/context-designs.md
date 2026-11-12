# Game Domain Design

The game domain provides framework-independent rules for a 15×15 Gomoku board. Its game service lives in `src/app/domain/game/service/game_service.py` and has no Django or database dependencies.

## Game Service

The game service initializes boards, validates moves, places stones, and checks for a win. A move wins when it completes at least five consecutive stones horizontally, vertically, or diagonally.

```python
initialize_board() -> Board
validate_board(board: object) -> None
validate_move(board: Board, x: int, y: int, player: int) -> None
place_stone(board: Board, x: int, y: int, player: int) -> bool
has_won(board: Board, x: int, y: int, player: int) -> bool
apply_move(state: GameState, move: Move) -> GameState
```

`validate_board` rejects malformed boards or cells other than integer `0`, `1`, and `2`. `validate_move` calls it before accessing the board. `validate_move` raises an error for invalid coordinates, players, board dimensions, or occupied positions. `place_stone` validates the move, updates the board, and returns whether it wins. `has_won` counts consecutive `player` stones through `(x, y)` without checking `board[y][x]`; callers must ensure that cell already contains `player`. `place_stone` sets the cell before calling `has_won`.

## State Transition Contract

`app.domain.game.state` defines the framework-independent data contract for a complete state transition and for repository/application-service integration:

```python
@dataclass(slots=True)
class GameState:
    board: Board
    current_player: Player
    status: GameStatus
    winner: Player | None = None

@dataclass(frozen=True, slots=True)
class Move:
    x: int
    y: int

def apply_move(state: GameState, move: Move) -> GameState: ...
```

`Player` is `Literal[1, 2]`; `Board` is a 15×15 `list[list[Literal[0, 1, 2]]]`. `GameStatus` has the persisted values `in_progress`, `won`, and `draw`. `GameState` contains rule-relevant values only; database IDs and timestamps remain persistence metadata. A move contains coordinates only. The transition uses `state.current_player` as the moving player, so callers cannot select whose turn it is through the move input. Because the board is mutable, a successful transition must copy the board and each row before applying a move; it returns a new state and leaves the input state unchanged.

| Type | Field | Type | Meaning |
| --- | --- | --- | --- |
| `GameState` | `board` | `Board` | Fifteen rows and columns, indexed as `board[y][x]`. |
| `GameState` | `current_player` | `Player` | Side to move while in progress; terminal states retain the last mover. |
| `GameState` | `status` | `GameStatus` | `in_progress`, `won`, or `draw`. |
| `GameState` | `winner` | `Player \| None` | Winning side; set only when status is `won`. |
| `Move` | `x`, `y` | `int` | Column and row of the requested position, each from `0` to `14`. |
| `IllegalMoveError` | `reason` | `IllegalMoveReason` | Stable rejection code for callers. |

Valid state values follow the existing persistence constraint: a `won` state has a winner, while `in_progress` and `draw` states have no winner.

An illegal move raises `IllegalMoveError`, a `ValueError` subclass, with a machine-readable `reason: IllegalMoveReason`. Reasons are `invalid_coordinate`, `out_of_bounds`, `occupied`, and `game_finished`. Callers should branch on `reason`, not parse the exception message. Transport layers can map these reasons to response codes and user-facing messages. Authentication or participant authorization is outside this move contract.

| Reason | Meaning |
| --- | --- |
| `invalid_coordinate` | A coordinate is not an integer. |
| `out_of_bounds` | A coordinate is outside `0` through `14`. |
| `occupied` | The target cell already contains a stone. |
| `game_finished` | The state is already won or drawn. |

`apply_move` validates that the game is in progress and the requested coordinates identify an empty board cell. It places the stone for `state.current_player`, checks for a win before checking for a full-board draw, and returns a new state. An in-progress game switches to the other player; a winning or drawing move retains the last mover in `current_player`. The input state and each of its board rows remain unchanged. Malformed state data raises `ValueError`; expected illegal moves raise `IllegalMoveError` with the reason codes above.

## Board Data

`Board` is a `list[list[Cell]]` indexed by row and then column (`board[y][x]`).

| Element | Type | Description |
| --- | --- | --- |
| Board | `list[list[Literal[0, 1, 2]]]` | Fifteen rows of fifteen cells. |
| Cell | `Literal[0, 1, 2]` | `0` for empty, `1` or `2` for a player's stone. |
| Coordinates | `int` | `x` and `y` each range from `0` to `14`. |

## Repository and Application Service

`GameRepository` maps Django's `Game` model to independent `GameState` values and keeps ORM models inside the persistence layer. `GameApplicationService` creates and retrieves games and coordinates move commands. An API can call the application service without importing ORM models.

```python
class GameRepository:
    def create(self, state: GameState) -> tuple[UUID, GameState]: ...
    def get(self, game_id: UUID) -> GameState: ...
    def get_for_update(self, game_id: UUID) -> GameState: ...
    def save(self, game_id: UUID, state: GameState) -> GameState: ...

class GameApplicationService:
    def __init__(self, repository: GameRepository | None = None) -> None: ...
    def create_game(self) -> tuple[UUID, GameState]: ...
    def get_game(self, game_id: UUID) -> GameState: ...
    def place_move(self, game_id: UUID, move: Move) -> GameState: ...
```

A new game has an empty board, player 1 to move, `in_progress` status, and no winner. Missing identifiers raise `GameNotFoundError`, a `LookupError`. `get_for_update` requires an active transaction. Callers performing read-modify-write operations must hold that lock until `save` completes. `place_move` opens an atomic transaction, locks the game row, validates and places the current player's stone using the game service, and saves the resulting state. A winning move sets the winner and status; a full board without a winner is a draw; otherwise the turn advances. Finished games and illegal coordinates or occupied cells raise `IllegalMoveError` with the reasons listed above. Failure rolls back the update. Concurrent moves for one game are serialized by the row lock and validated against the latest committed state; different games can proceed independently.

The application service calls `apply_move` to apply the state transition.

## Web Interface

The browser interface creates and loads games through the [game API](apis.md) and renders the 15×15 board, current turn, and win or draw result. It stores the last game ID in browser local storage so the game can be restored when the page is reloaded. A game ID can also be entered to load an existing game. Errors are shown to the player, and the browser obtains a CSRF cookie before sending state-changing requests.

Games have no account or participant authorization. Anyone with a game ID can access and play that game. The interface is intended for two people taking turns on the same device; it does not receive real-time updates from other clients.
