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
select_cpu_move(board: Board) -> Move | None  # Proposed
```

`validate_board` rejects malformed boards or cells other than integer `0`, `1`, and `2`. `validate_move` calls it before accessing the board. `validate_move` raises an error for invalid coordinates, players, board dimensions, or occupied positions. `place_stone` validates the move, updates the board, and returns whether it wins. `has_won` counts consecutive `player` stones through `(x, y)` without checking `board[y][x]`; callers must ensure that cell already contains `player`. `place_stone` sets the cell before calling `has_won`.

### CPU move selection

The proposed selector takes a board for a pending white turn. It considers at most 225 intersections and returns a legal white move, or `None` when the board has no empty cell. It first looks for an immediate white win, then for an immediate black win to block. With no immediate win or threat, it prefers the smallest squared distance to the center `(7, 7)`. Ties among wins, blocks, or equally distant fallback moves use ascending row and then column. The selector uses the existing win logic and leaves the input board unchanged.

## State Transition Contract

`app.domain.game.state` defines the framework-independent data contract for a complete state transition and for repository/application-service integration:

```python
@dataclass(slots=True)
class GameState:
    board: Board
    current_player: Player
    status: GameStatus
    winner: Player | None = None
    mode: GameMode = GameMode.TWO_PLAYER  # Proposed

    @property
    def revision(self) -> int: ...  # Proposed

@dataclass(frozen=True, slots=True)
class Move:
    x: int
    y: int

def apply_move(state: GameState, move: Move) -> GameState: ...
```

`Player` is `Literal[1, 2]`. `Board` is a 15×15 `list[list[Literal[0, 1, 2]]]`. `GameStatus` has the persisted values `in_progress`, `won`, and `draw`. Database IDs and timestamps remain persistence metadata. A move contains coordinates only. The transition uses `state.current_player` as the moving player, so callers cannot select whose turn it is through the move input. Because the board is mutable, a successful transition copies the board and each row before applying a move. It returns a new state and leaves the input state unchanged.

| Type | Field | Type | Meaning |
| --- | --- | --- | --- |
| `GameState` | `board` | `Board` | Fifteen rows and columns, indexed as `board[y][x]`. |
| `GameState` | `current_player` | `Player` | Side to move while in progress; terminal states retain the last mover. |
| `GameState` | `status` | `GameStatus` | `in_progress`, `won`, or `draw`. |
| `GameState` | `winner` | `Player \| None` | Winning side; set only when status is `won`. |
| `GameState` | `mode` (proposed) | `GameMode` | `TWO_PLAYER` or `CPU`, persisted as `two_player` or `cpu`. Defaults to `TWO_PLAYER`. |
| `GameState` | `revision` (proposed) | `int` | Derived occupied-cell count. It starts at zero and increases by one per saved stone. |
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

Under the CPU proposal, both modes use the same board, win, and draw rules. Every state returned by `apply_move`, including a win or draw, carries forward the input mode.

## Board Data

`Board` is a `list[list[Cell]]` indexed by row and then column (`board[y][x]`).

| Element | Type | Description |
| --- | --- | --- |
| Board | `list[list[Literal[0, 1, 2]]]` | Fifteen rows of fifteen cells. |
| Cell | `Literal[0, 1, 2]` | `0` for empty, `1` or `2` for a player's stone. |
| Coordinates | `int` | `x` and `y` each range from `0` to `14`. |

## Repository and Application Service

`GameRepository` maps Django's `Game` model to independent `GameState` values and keeps ORM models inside the persistence layer. `GameApplicationService` creates and retrieves games and coordinates move commands. An API can call the application service without importing ORM models.

The signatures below include the proposed `mode` and `expected_revision` parameters and CPU advance command.

```python
class GameRepository:
    def create(self, state: GameState) -> tuple[UUID, GameState]: ...
    def get(self, game_id: UUID) -> GameState: ...
    def get_for_update(self, game_id: UUID) -> GameState: ...
    def save(self, game_id: UUID, state: GameState) -> GameState: ...

class GameApplicationService:
    def __init__(self, repository: GameRepository | None = None) -> None: ...
    def create_game(
        self, mode: GameMode = GameMode.TWO_PLAYER
    ) -> tuple[UUID, GameState]: ...
    def get_game(self, game_id: UUID) -> GameState: ...
    def place_move(
        self, game_id: UUID, move: Move, expected_revision: int | None = None
    ) -> GameState: ...
    def advance_cpu(self, game_id: UUID, expected_revision: int) -> GameState: ...
```

A new game has an empty board, player 1 to move, `in_progress` status, and no winner. Missing identifiers raise `GameNotFoundError`, a `LookupError`. `get_for_update` requires an active transaction. Callers performing read-modify-write operations must hold that lock until `save` completes. `place_move` opens an atomic transaction, locks the game row, validates and places the current player's stone using the game service, and saves the resulting state. A winning move sets the winner and status; a full board without a winner is a draw; otherwise the turn advances. Finished games and illegal coordinates or occupied cells raise `IllegalMoveError` with the reasons listed above. Failure rolls back the update. Concurrent moves for one game are serialized by the row lock and validated against the latest committed state; different games can proceed independently.

The application service calls `apply_move` to apply the state transition.

### Turn ownership and transactions

Under the CPU proposal, the repository reads mode on load and writes it on creation. Move saves leave the stored mode unchanged. A CPU game starts with human black to move. The human move command checks the expected revision and black's turn under the game row lock, then applies the rules transition. A nonterminal black move commits as a pending CPU turn. A terminal move commits the result immediately.

The CPU advance command opens its own transaction and re-reads the state under the same row lock. It rejects the command for a two-player game. For a CPU game it advances only when the supplied revision matches the locked state, the game is in progress, and white is next. In every other CPU state it returns the saved position without writing. An eligible command applies the selected move through `apply_move` and saves the resulting state. A selector or persistence failure rolls back only the CPU transaction. The preceding human stone remains available from GET.

Two simultaneous requests for the same pending revision serialize on the row. The first accepted command adds one stone, so the next request sees a different revision. The same comparison prevents a delayed request from advancing a later white turn. Human requests in CPU games use the revision to prevent the same replay across black turns. Two-player games continue to accept coordinate-only moves for whichever human color is next.

## Web Interface

The browser interface creates and loads games through the [game API](apis.md) and renders the 15×15 board, current turn, and win or draw result. It stores the last game ID in browser local storage so the game can be restored when the page is reloaded. A game ID can also be entered to load an existing game. Errors are shown to the player, and the browser obtains a CSRF cookie before sending state-changing requests.

Games have no account or participant authorization. Anyone with a game ID can access and play that game. In two-player mode, two people take turns on the same device. The browser does not receive real-time updates from other clients.

### CPU play and recovery

Under the proposed [CPU mode](../../product-specs/local-cpu-game.md), the browser offers a mode choice at creation and identifies the active mode, human color, turn, and result. It renders the confirmed human stone and announces the CPU turn before requesting that turn. Pointer and keyboard placement remain blocked until black can act again. A terminal response ends placement immediately and a terminal human move sends no CPU request.

Manual load by ID, refresh, and automatic restore can resume a saved white turn. If a CPU request fails, the page retains the last confirmed board and offers a keyboard-accessible retry. Retry reads the saved game first and sends a CPU command only for the revision of the pending turn it observes. After an uncertain human POST, the browser reloads the game by ID before allowing placement again. It restores board focus when play resumes and retains the saved ID, Copy ID action, and manual copy fallback.

A successful response to a stale CPU request can report a newer pending white turn. Render the returned board, keep human placement disabled, and request that turn using the returned revision. If the active game has changed while a request was in flight, discard the old game's response.
