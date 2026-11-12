"""Framework-agnostic Gomoku game rules."""

from app.domain.game.state import (
    Board,
    GameState,
    GameStatus,
    IllegalMoveError,
    IllegalMoveReason,
    Move,
    Player,
)

BOARD_SIZE = 15
WIN_LENGTH = 5
EMPTY = 0


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
    if type(player) is not int or player not in (1, 2):
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


def apply_move(state: GameState, move: Move) -> GameState:
    """Apply a move and return a new state without mutating the input state."""
    if not isinstance(state.status, GameStatus):
        raise ValueError("Game state has an invalid status")
    if type(state.current_player) is not int or state.current_player not in (1, 2):
        raise ValueError("Game state has an invalid current player")
    if state.status is GameStatus.WON:
        if type(state.winner) is not int or state.winner not in (1, 2):
            raise ValueError("A won game must have a valid winner")
    elif state.winner is not None:
        raise ValueError("An in-progress or drawn game cannot have a winner")
    validate_board(state.board)
    if state.status in (GameStatus.WON, GameStatus.DRAW):
        raise IllegalMoveError(IllegalMoveReason.GAME_FINISHED)

    if not isinstance(move, Move):
        raise TypeError("Move must be a Move instance")
    if type(move.x) is not int or type(move.y) is not int:
        raise IllegalMoveError(IllegalMoveReason.INVALID_COORDINATE)
    if not 0 <= move.x < BOARD_SIZE or not 0 <= move.y < BOARD_SIZE:
        raise IllegalMoveError(IllegalMoveReason.OUT_OF_BOUNDS)
    if state.board[move.y][move.x] != EMPTY:
        raise IllegalMoveError(IllegalMoveReason.OCCUPIED)

    board = [row.copy() for row in state.board]
    player: Player = state.current_player
    board[move.y][move.x] = player

    if has_won(board, move.x, move.y, player):
        status = GameStatus.WON
        winner = player
        current_player = player
    elif all(cell != EMPTY for row in board for cell in row):
        status = GameStatus.DRAW
        winner = None
        current_player = player
    else:
        status = GameStatus.IN_PROGRESS
        winner = None
        current_player = 2 if player == 1 else 1

    return GameState(
        board=board,
        current_player=current_player,
        status=status,
        winner=winner,
    )
