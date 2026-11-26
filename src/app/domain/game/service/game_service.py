"""Framework-agnostic Gomoku game rules."""

from collections.abc import Collection
from dataclasses import replace

from app.domain.game.state import (
    Board,
    Cell,
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
_WIN_DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))
_WIN_WINDOWS = tuple(
    tuple((y + dy * step) * BOARD_SIZE + x + dx * step for step in range(WIN_LENGTH))
    for y in range(BOARD_SIZE)
    for x in range(BOARD_SIZE)
    for dx, dy in _WIN_DIRECTIONS
    if 0 <= x + dx * (WIN_LENGTH - 1) < BOARD_SIZE
    and 0 <= y + dy * (WIN_LENGTH - 1) < BOARD_SIZE
)


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
    for dx, dy in _WIN_DIRECTIONS:
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

    return replace(
        state,
        board=board,
        current_player=current_player,
        status=status,
        winner=winner,
    )


def select_cpu_move(board: Board) -> Move | None:
    """Prefer an immediate win, an immediate block, and a forcing win in order."""
    validate_board(board)
    candidate_board = [row.copy() for row in board]
    center = BOARD_SIZE // 2
    block = None
    fallback = None
    closest_distance = BOARD_SIZE**2

    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            if cell != EMPTY:
                continue
            # has_won counts the stone at the pivot, so evaluate each color
            # with that cell filled and restore it before the next candidate.
            candidate_board[y][x] = 2
            if has_won(candidate_board, x, y, 2):
                return Move(x, y)
            if block is None:
                candidate_board[y][x] = 1
                if has_won(candidate_board, x, y, 1):
                    block = Move(x, y)
            candidate_board[y][x] = EMPTY
            distance = (x - center) ** 2 + (y - center) ** 2
            if distance < closest_distance:
                closest_distance = distance
                fallback = Move(x, y)
    if block is not None or fallback is None:
        return block
    return _find_tactical_move(board) or fallback


def _find_tactical_move(board: Board) -> Move | None:
    """Find a forced win on white's next turn or an effective defense."""
    cells = [cell for row in board for cell in row]
    if all(cells.count(player) < WIN_LENGTH - 2 for player in (1, 2)):
        return None

    completions = _two_move_completions(cells)
    white_wins = completions[2]
    forced_win = min(_double_threats(white_wins), key=_center_priority, default=None)
    if forced_win is not None:
        # Black had no immediate win and can occupy at most one winning point.
        y, x = divmod(forced_win, BOARD_SIZE)
        return Move(x, y)

    threats = _double_threats(completions[1])
    if not threats:
        return None

    forcing_candidates = sorted(
        (candidate for candidate, wins in white_wins.items() if len(wins) == 1),
        key=_center_priority,
    )
    for candidate in forcing_candidates:
        wins = white_wins[candidate]
        if _stops_threats(candidate, wins, threats) and _has_safe_follow_up(
            cells, candidate, next(iter(wins)), completions[1]
        ):
            y, x = divmod(candidate, BOARD_SIZE)
            return Move(x, y)

    for candidate in sorted(
        (position for position, cell in enumerate(cells) if cell == EMPTY),
        key=_center_priority,
    ):
        if _stops_threats(candidate, white_wins.get(candidate, ()), threats):
            y, x = divmod(candidate, BOARD_SIZE)
            return Move(x, y)
    return None


def _center_priority(position: int) -> tuple[int, int]:
    y, x = divmod(position, BOARD_SIZE)
    center = BOARD_SIZE // 2
    return (x - center) ** 2 + (y - center) ** 2, position


def _two_move_completions(cells: list[Cell]) -> dict[Player, dict[int, set[int]]]:
    """Map first placements to the winning points they create."""
    completions: dict[Player, dict[int, set[int]]] = {1: {}, 2: {}}
    for window in _WIN_WINDOWS:
        values = [cells[position] for position in window]
        if values.count(EMPTY) != 2:
            continue
        # Both new stones belong to one five-cell window. Either empty
        # intersection can be the first placement.
        for player in completions:
            if values.count(player) == WIN_LENGTH - 2:
                first, second = (
                    position for position in window if cells[position] == EMPTY
                )
                completions[player].setdefault(first, set()).add(second)
                completions[player].setdefault(second, set()).add(first)
    return completions


def _double_threats(completions: dict[int, set[int]]) -> dict[int, set[int]]:
    return {reply: wins for reply, wins in completions.items() if len(wins) >= 2}


def _stops_threats(
    candidate: int, white_wins: Collection[int], threats: dict[int, set[int]]
) -> bool:
    return all(
        candidate == reply
        or len(black_wins - {candidate}) < 2
        or any(win != reply for win in white_wins)
        for reply, black_wins in threats.items()
    )


def _has_safe_follow_up(
    cells: list[Cell],
    defense: int,
    forced_block: int,
    black_completions: dict[int, set[int]],
) -> bool:
    # Neither color could win before the defense. The block removes white's
    # sole winning point and can leave black only wins that it just created.
    black_wins = set(black_completions.get(forced_block, ())) - {defense}
    if len(black_wins) > 1:
        return False

    position = cells.copy()
    position[defense] = 2
    position[forced_block] = 1
    completions = _two_move_completions(position)
    threats = _double_threats(completions[1])
    if not threats:
        # White can block the sole black win, play any empty cell, or draw
        # if the forced block filled the board.
        return True

    candidates = black_wins or (
        index for index, cell in enumerate(position) if cell == EMPTY
    )
    return any(
        _stops_threats(candidate, completions[2].get(candidate, ()), threats)
        for candidate in candidates
    )
