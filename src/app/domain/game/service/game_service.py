"""Framework-agnostic Gomoku game rules."""

BOARD_SIZE = 15
WIN_LENGTH = 5
EMPTY = 0

Board = list[list[int]]


def initialize_board() -> Board:
    """Return an empty 15 by 15 board."""
    return [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def validate_board(board: object) -> None:
    """Raise ValueError unless board is a 15 by 15 grid of valid stones."""
    if (
        not isinstance(board, list)
        or len(board) != BOARD_SIZE
        or any(not isinstance(row, list) or len(row) != BOARD_SIZE for row in board)
        or any(
            type(cell) is not int or cell not in (0, 1, 2)
            for row in board
            for cell in row
        )
    ):
        raise ValueError("Board must be 15 by 15 with cells 0, 1, or 2")


def validate_move(board: Board, x: int, y: int, player: int) -> None:
    """Raise an error when a move is invalid or the board is malformed."""
    if (
        not isinstance(x, int)
        or isinstance(x, bool)
        or not isinstance(y, int)
        or isinstance(y, bool)
    ):
        raise TypeError("Coordinates must be integers")
    if not 0 <= x < BOARD_SIZE or not 0 <= y < BOARD_SIZE:
        raise ValueError("Coordinates must be between 0 and 14")
    if player not in (1, 2):
        raise ValueError("Player must be 1 or 2")
    validate_board(board)
    if board[y][x] != EMPTY:
        raise ValueError("Position is already occupied")


def place_stone(board: Board, x: int, y: int, player: int) -> bool:
    """Place a stone and return whether this move wins the game."""
    validate_move(board, x, y, player)
    board[y][x] = player
    return has_won(board, x, y, player)


def has_won(board: Board, x: int, y: int, player: int) -> bool:
    """Return whether the stone at (x, y) completes five or more in a row."""
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        count = 1
        for direction in (-1, 1):
            step = 1
            while True:
                next_x = x + dx * step * direction
                next_y = y + dy * step * direction
                if not (0 <= next_x < BOARD_SIZE and 0 <= next_y < BOARD_SIZE):
                    break
                if board[next_y][next_x] != player:
                    break
                count += 1
                step += 1
        if count >= WIN_LENGTH:
            return True
    return False
