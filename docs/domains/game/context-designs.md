# Game Domain Design

Game rules live in `src/app/domain/game/service/game_service.py` and have no Django or database dependencies.

The board is a `list[list[int]]` with 15 rows and 15 columns. Empty cells are `0`; player stones are `1` or `2`.

- `initialize_board() -> Board`: create an empty board.
- `validate_move(board: Board, x: int, y: int, player: int) -> None`: validate coordinates, player, board dimensions, and occupancy; raise an error for invalid input.
- `place_stone(board: Board, x: int, y: int, player: int) -> bool`: validate and place a stone, then report whether the move wins.
- `has_won(board: Board, x: int, y: int, player: int) -> bool`: check whether the stone completes at least five consecutive stones horizontally, vertically, or diagonally.
