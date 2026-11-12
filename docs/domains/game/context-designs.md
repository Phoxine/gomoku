# Game Domain Design

The game domain provides framework-independent rules for a 15×15 Gomoku board. Its game service lives in `src/app/domain/game/service/game_service.py` and has no Django or database dependencies.

## Game Service

The game service initializes boards, validates moves, places stones, and checks for a win. A move wins when it completes at least five consecutive stones horizontally, vertically, or diagonally.

```python
initialize_board() -> Board
validate_move(board: Board, x: int, y: int, player: int) -> None
place_stone(board: Board, x: int, y: int, player: int) -> bool
has_won(board: Board, x: int, y: int, player: int) -> bool
```

`validate_move` raises an error for invalid coordinates, players, board dimensions, or occupied positions. `place_stone` validates the move, updates the board, and returns whether it wins. `has_won` checks the stone at the specified position.

## Board Data

`Board` is a `list[list[int]]` indexed by row and then column (`board[y][x]`).

| Element | Type | Description |
| --- | --- | --- |
| Board | `list[list[int]]` | Fifteen rows of fifteen cells. |
| Cell | `int` | `0` for empty, `1` or `2` for a player's stone. |
| Coordinates | `int` | `x` and `y` each range from `0` to `14`. |
