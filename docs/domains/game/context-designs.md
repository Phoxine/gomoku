# Game Domain Design

The game domain provides framework-independent rules for a 15×15 Gomoku board. Its game service lives in `src/app/domain/game/service/game_service.py` and has no Django or database dependencies.

## Game Service

The game service initializes boards, validates moves, places stones, checks for a win, and selects CPU moves. In the default rules, at least five consecutive stones win horizontally, vertically, or diagonally. Enabled policies change black's win rule to exactly five.

```python
initialize_board() -> Board
validate_board(board: object) -> None
validate_move(board: Board, x: int, y: int, player: int) -> None
place_stone(board: Board, x: int, y: int, player: int) -> bool
has_won(board: Board, x: int, y: int, player: int) -> bool
apply_move(state: GameState, move: Move) -> GameState
select_cpu_move(
    board: Board, policy: ForbiddenMovePolicy = ForbiddenMovePolicy.OFF
) -> Move | None
```

`validate_board` rejects malformed boards or cells other than integer `0`, `1`, and `2`. `validate_move` calls it before accessing the board. `validate_move` raises an error for invalid coordinates, players, board dimensions, or occupied positions. `place_stone` validates the move, updates the board, and returns whether it wins. `has_won` counts consecutive `player` stones through `(x, y)` without checking `board[y][x]`; callers must ensure that cell already contains `player`. `place_stone` sets the cell before calling `has_won`.

### Black forbidden-move evaluation

Evaluate an empty intersection using a temporary board and the new black stone as the pivot. Check exact five in every direction before reporting a foul. With no exact five, check overline first, then double-four, then double-three. Count distinct formations through the pivot by axis and stone coordinates. A single straight four counts once even when both ends win. A double-four can consist of two formations on one axis. Require an exact-five completion for each four. To count a three, require an extension that creates a straight four with two winning ends. An extension that makes five or is forbidden does not qualify. Reapply the double-three definition to candidate extensions on temporary boards. [RIF rules §§3 and 9](https://www.renju.net/rifrules/)

After the ordinary move checks, `apply_move` uses the saved policy. Warn rejects a forbidden black move before any save and exposes the typed reason as `ForbiddenMoveError.forbidden_reason`. Loss accepts the forbidden move as the final stone and sets white as winner with the specific result reason. After a non-winning white move in Warn, check for a full-board draw first. If the board still has empty cells but no legal black move, set a white win with `no_legal_black_move`. Both terminal outcomes retain the last mover. The application service saves the transition and its accepted stone together.

### CPU move selection

`select_cpu_move` takes a board for a pending white turn and returns a legal white move, or `None` when the board has no empty cell. It applies the same rules as `apply_move` and leaves the input board unchanged. The following tactical priorities describe Off.

1. Take an immediate white win if available. Otherwise, block an immediate black winning intersection if one exists. If several moves qualify at either step, choose the first in ascending row and column order.
2. With neither immediate win available, prefer a white move that creates at least two distinct winning intersections for white's next turn. Black has no immediate win and can occupy at most one of these intersections. This priority applies whether or not black has a forcing reply. Choose by squared distance to the center `(7, 7)`, then ascending row and column.
3. Otherwise, look one black reply ahead. A reply threatens a forced loss if it leaves at least two distinct empty intersections where black could win on its next turn and leaves white no immediate win. These intersections may come from gapped or crossing patterns. To defend, white can occupy the reply, remove enough black winning intersections, or leave white an immediate win after the reply. Among moves that defend against every forcing reply, prefer those that create exactly one immediate white winning intersection and pass the follow-up check below. Rank moves in this group by the same distance and coordinate ordering.
4. If no move qualifies for that preference, choose the white move that leaves the fewest distinct forcing black replies. A complete defense leaves zero, and each remaining black reply counts once even if it creates more than two winning intersections. Break ties by the same distance and coordinate ordering. With no forcing black replies to defend against, choose the closest legal intersection using that ordering.

A defense qualifies for preference only if black has no immediate win after the white placement. Simulate black occupying the single white winning intersection. The defense passes the follow-up check if that block ends the game in a draw, or if white has a legal next move that wins immediately or leaves black with neither an immediate win nor a forcing double-threat reply. A white follow-up that blocks an immediate black win must also stop any remaining forcing replies. The search considers only that black block and the next white placement, using the base tactical rules without repeating the forcing-defense ranking.

The lookahead examines consecutive groups of five intersections on the 15×15 board in the same four directions as the win check. Once immediate wins are ruled out, a win in two placements must use a group with three stones of the same color and two empty intersections. Either empty intersection can be played first, and the other is then a winning intersection for that color. The selector collects these winning intersections by first placement, using sets to count each coordinate once.

Under Off, a white defense can only reduce black's options, so the selector rechecks the black replies that had at least two winning intersections on the original board. It excludes replies and winning intersections occupied by the defense. If a black reply still has two winning intersections, the selector checks whether the defense leaves white a winning intersection that the black reply did not occupy.

In the follow-up check, black's block occupies white's sole winning intersection. The selector finds black's immediate winning points from the two-placement wins that start at the block, excluding the point already occupied by the white defense. If the block creates two or more immediate black wins, the defense fails the check. If it creates exactly one, only a white move at that winning intersection can qualify as a follow-up. The selector reevaluates double threats on a copy of the position after the defense and block.

With Warn or Loss enabled, predict black wins using exact five and count only legal black continuations as threats. Re-evaluate relevant black replies after simulated white placements. Blocking a line can make a previously forbidden black reply legal. A forbidden black block cannot defend against a white win. Consider available legal replies and the Warn terminal outcome when no legal reply remains. Score a white move that ends the game under Warn as an immediate win.

## State Transition Contract

`app.domain.game.state` defines the framework-independent data contract for a complete state transition and for repository/application-service integration:

```python
@dataclass(slots=True)
class GameState:
    board: Board
    current_player: Player
    status: GameStatus
    winner: Player | None = None
    mode: GameMode = GameMode.TWO_PLAYER
    forbidden_move_policy: ForbiddenMovePolicy = ForbiddenMovePolicy.OFF
    result_reason: GameResultReason | None = None

    @property
    def revision(self) -> int: ...

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
| `GameState` | `mode` | `GameMode` | `TWO_PLAYER` or `CPU`, persisted as `two_player` or `cpu`. Defaults to `TWO_PLAYER`. |
| `GameState` | `forbidden_move_policy` | `ForbiddenMovePolicy` | `off`, `warn`, or `loss`. Fixed at creation. |
| `GameState` | `result_reason` | `GameResultReason \| None` | `overline`, `double_four`, `double_three`, or `no_legal_black_move` for white wins under the enabled policies. Null otherwise. |
| `GameState` | `revision` | `int` | Derived occupied-cell count. It starts at zero and increases by one per saved stone. |
| `Move` | `x`, `y` | `int` | Column and row of the requested position, each from `0` to `14`. |
| `IllegalMoveError` | `reason` | `IllegalMoveReason` | Stable rejection code for callers. |

Valid state values follow the existing persistence constraint: a `won` state has a winner, while `in_progress` and `draw` states have no winner.

An illegal move raises `IllegalMoveError`, a `ValueError` subclass, with a machine-readable `reason: IllegalMoveReason`. The rules service emits the reasons below. Callers can use `reason` to map errors to response codes and user-facing messages. Authentication or participant authorization is outside this move contract.

| Reason | Meaning |
| --- | --- |
| `invalid_coordinate` | A coordinate is not an integer. |
| `out_of_bounds` | A coordinate is outside `0` through `14`. |
| `occupied` | The target cell already contains a stone. |
| `game_finished` | The state is already won or drawn. |
| `forbidden_move` | Warn rejected a black move. Carries the specific forbidden-move reason. |

`apply_move` validates that the game is in progress and the requested coordinates identify an empty board cell. It places the stone for `state.current_player`, checks for a win before checking for a full-board draw, and returns a new state. An in-progress game switches to the other player; a winning or drawing move retains the last mover in `current_player`. The input state and each of its board rows remain unchanged. Malformed state data raises `ValueError`; expected illegal moves raise `IllegalMoveError` with the reason codes above.

Both modes use the same rules for the saved policy. Every state returned by `apply_move` carries forward the input mode and policy.

## Board Data

`Board` is a `list[list[Cell]]` indexed by row and then column (`board[y][x]`).

| Element | Type | Description |
| --- | --- | --- |
| Board | `list[list[Literal[0, 1, 2]]]` | Fifteen rows of fifteen cells. |
| Cell | `Literal[0, 1, 2]` | `0` for empty, `1` or `2` for a player's stone. |
| Coordinates | `int` | `x` and `y` each range from `0` to `14`. |

## Repository and Application Service

`GameRepository` maps Django's `Game` model to independent `GameState` values and keeps ORM models inside the persistence layer. It writes mode and policy on creation, preserves them on move saves, and saves the terminal reason with the result. `GameApplicationService` creates and retrieves games and coordinates human and CPU move commands. An API can call the application service without importing ORM models.

```python
class GameRepository:
    def create(self, state: GameState) -> tuple[UUID, GameState]: ...
    def get(self, game_id: UUID) -> GameState: ...
    def get_for_update(self, game_id: UUID) -> GameState: ...
    def save(self, game_id: UUID, state: GameState) -> GameState: ...
    def save_move(
        self, game_id: UUID, state: GameState, move: Move, player: Player
    ) -> GameState: ...
    def read_verified_history(self, game_id: UUID) -> GameHistory: ...

class GameApplicationService:
    def __init__(self, repository: GameRepository | None = None) -> None: ...
    def create_game(
        self,
        mode: GameMode = GameMode.TWO_PLAYER,
        forbidden_move_policy: ForbiddenMovePolicy = ForbiddenMovePolicy.OFF,
    ) -> tuple[UUID, GameState]: ...
    def get_game(self, game_id: UUID) -> GameState: ...
    def place_move(
        self, game_id: UUID, move: Move, expected_revision: int | None = None
    ) -> GameState: ...
    def advance_cpu(self, game_id: UUID, expected_revision: int) -> GameState: ...
```

A new game has an empty board, black to move, `in_progress` status, and no winner. Missing identifiers raise `GameNotFoundError`, a `LookupError`.

### Turn ownership and transactions

`place_move` and `advance_cpu` each start an atomic transaction and acquire the game row lock through `get_for_update`. An accepted command calls `apply_move` and persists the resulting state before the transaction commits. The row lock serializes commands for the same game while different games can proceed independently.

Both commands persist accepted moves through `save_move`. The application service supplies the mover from the locked pre-move state. The repository saves the new snapshot and inserts one move row in the command's transaction. It uses the resulting revision as the move number, including for a win or draw. A failure in either write rolls back the command.

In CPU mode, the human plays black. Under the row lock, `place_move` checks that CPU requests include an expected revision and two-player requests omit it. In an active CPU game, it also verifies black's turn and compares the expected revision with the saved board's occupied-cell count. A nonterminal black move commits as a pending CPU turn. A terminal black move commits the result immediately.

The CPU advance command rejects two-player games. For a CPU game it advances only when the supplied revision matches the locked state, the game is in progress, and white is next. It supplies the locked game's policy to the selector. In every other CPU state it returns the saved position without writing. A selector or persistence failure rolls back the CPU transaction. The preceding human stone remains available from GET.

Two simultaneous requests for the same pending revision serialize on the row. The first accepted command adds one stone, so the next request sees a different revision. The same comparison prevents a delayed request from advancing a later white turn and prevents replay across black turns. Two-player games accept coordinate-only moves for whichever human color is next. The application service uses `IllegalMoveError` for mode and turn rejections, as documented in the [game API](apis.md).

### Verified move history

| Record | Field | Type | Meaning |
| --- | --- | --- | --- |
| `GameHistory` | `state` | `GameState` | Snapshot checked against the recorded moves. |
| `GameHistory` | `start_revision` | `int` | Occupied-cell count when recording began. |
| `GameHistory` | `moves` | `tuple[RecordedMove, ...]` | Verified moves in ascending order. |
| `RecordedMove` | `move_number` | `int` | Board revision immediately after the stone. |
| `RecordedMove` | `move` | `Move` | Coordinates of the accepted stone. |
| `RecordedMove` | `player` | `Player` | Color of the accepted stone. |

The internal history reader locks the game row while reading its snapshot, boundary, and move rows ordered by number. The lock serializes this read with the move commands. For snapshot revision `r` and boundary `b`, the reader requires `0 <= b <= r` and exactly the move numbers `b + 1` through `r`. It checks each recorded position and color against the snapshot. A boundary beyond the snapshot, a gap, an unexpected row, or a color mismatch raises `InconsistentGameHistoryError`. An empty history is valid when `b == r`. An unknown game ID raises `GameNotFoundError`.

For a game with boundary zero, the verified rows contain the complete move sequence. To reproduce the position, turn, and result, replay the moves through `apply_move` from an empty board using the saved policy. A forbidden-move loss records its final black stone, and a Warn rejection produces no move row. For an older game, the rows describe only the moves accepted after recording began. The board at the start of that range can be recovered by clearing the recorded positions from the saved snapshot. The order of stones already on that board is unavailable.

The [game API](apis.md) continues to serve the saved board snapshot for loading and resuming play. History readback is internal.

## Web Interface

The browser interface creates and loads games through the [game API](apis.md) and renders the 15×15 board, current turn, and win or draw result. It stores the last game ID in browser local storage so the game can be restored when the page is reloaded. A game ID can also be entered to load an existing game. Errors are shown to the player, and the browser obtains a CSRF cookie before sending state-changing requests.

Games have no account or participant authorization. Anyone with a game ID can access and play that game. In two-player mode, two people take turns on the same device. The browser does not receive real-time updates from other clients.

The board renders a translucent hover preview on enabled empty intersections. Its color comes from the active game's `current_player`. The preview is unavailable whenever placement is disabled, including while a request is in progress, while waiting for the CPU, when the saved turn needs confirmation, and after the game ends.

The browser sends the new-game rule settings when creating a game and displays the saved policy with the active game. A Warn response opens a modal dialog with the rejection reason and leaves the same black turn available. Closing it with **Choose another move** or Escape focuses the nearest available board intersection. A forbidden-move loss disables placement and opens the result dialog using the saved `result_reason`, both on receipt of the result and when a saved game is restored. Closing it with **Back to board** or Escape focuses **View result details**, which reopens the dialog. A white win because black has no legal move displays its reason in the board status.

### CPU play and recovery

The browser offers a mode choice at creation and identifies the active mode, human color, turn, and result for [CPU games](../../product-specs/local-cpu-game.md). It renders the confirmed human stone and announces the CPU turn before requesting that turn. Pointer and keyboard placement remain blocked until black can act again. A terminal response ends placement immediately and a terminal human move sends no CPU request.

Manual load by ID, refresh, and automatic restore can resume a saved white turn. If a CPU request fails, the page retains the last confirmed board and offers a keyboard-accessible retry. Retry reads the saved game first and sends a CPU command only for the revision of the pending turn it observes. After an uncertain human POST, the browser reloads the game by ID before allowing placement again. If that read fails, the board stays disabled and the player can reload the saved game. The page restores board focus when play resumes and focus has not moved to another control. It retains the saved ID, Copy ID action, and manual copy fallback.

A successful response to a stale CPU request can report a newer pending white turn. The browser renders that board, keeps human placement disabled, and requests the new turn using the returned revision. Game controls that replace the active game remain disabled until the current request finishes.
