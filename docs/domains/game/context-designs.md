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
| `GameState` | `current_player` | `Player` | Side that will make the next move. |
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

The state-transition operation is a contract for the next implementation step; this change defines its shared types and failure semantics without implementing turn changes, win/draw transitions, or persistence.

## Board Data

`Board` is a `list[list[Cell]]` indexed by row and then column (`board[y][x]`).

| Element | Type | Description |
| --- | --- | --- |
| Board | `list[list[Literal[0, 1, 2]]]` | Fifteen rows of fifteen cells. |
| Cell | `Literal[0, 1, 2]` | `0` for empty, `1` or `2` for a player's stone. |
| Coordinates | `int` | `x` and `y` each range from `0` to `14`. |
