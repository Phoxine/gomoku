"""Framework-agnostic Gomoku game rules."""

from collections.abc import Collection, Iterator
from dataclasses import replace
from itertools import islice

from app.domain.game.state import (
    Board,
    Cell,
    ForbiddenMoveError,
    ForbiddenMovePolicy,
    ForbiddenMoveReason,
    GameResultReason,
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
    return any(
        _line_length(board, x, y, dx, dy, player) >= WIN_LENGTH
        for dx, dy in _WIN_DIRECTIONS
    )


def _line_length(board: Board, x: int, y: int, dx: int, dy: int, player: int) -> int:
    count = 1
    for direction in (-1, 1):
        next_x, next_y = x + dx * direction, y + dy * direction
        while (
            0 <= next_x < BOARD_SIZE
            and 0 <= next_y < BOARD_SIZE
            and board[next_y][next_x] == player
        ):
            count += 1
            next_x += dx * direction
            next_y += dy * direction
    return count


def _black_axis(board: Board, move: Move, dx: int, dy: int) -> tuple[Cell, ...]:
    # Five points on each side include the cells beyond both possible ends
    # of a five through the pivot. Treat the edge like a white stone.
    cells: list[Cell] = []
    for offset in range(-WIN_LENGTH, WIN_LENGTH + 1):
        x, y = move.x + offset * dx, move.y + offset * dy
        cells.append(board[y][x] if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE else 2)
    return tuple(cells)


def _black_outcome(board: Board, move: Move) -> tuple[bool, ForbiddenMoveReason | None]:
    """Evaluate a black stone already placed on a temporary board."""
    lengths = [
        _line_length(board, move.x, move.y, dx, dy, 1) for dx, dy in _WIN_DIRECTIONS
    ]
    if WIN_LENGTH in lengths:
        return True, None
    if max(lengths) > WIN_LENGTH:
        return False, ForbiddenMoveReason.OVERLINE

    axes = [_black_axis(board, move, dx, dy) for dx, dy in _WIN_DIRECTIONS]
    four_count = 0
    for axis in axes:
        fours = set()
        for start in range(1, WIN_LENGTH + 1):
            end = start + WIN_LENGTH
            window = axis[start:end]
            if (
                window.count(1) == 4
                and EMPTY in window
                and axis[start - 1] != 1
                and axis[end] != 1
            ):
                fours.add(
                    tuple(index for index in range(start, end) if axis[index] == 1)
                )
        four_count += len(fours)
        if four_count >= 2:
            return False, ForbiddenMoveReason.DOUBLE_FOUR

    threes: dict[tuple[int, tuple[int, ...]], set[Move]] = {}
    for axis_index, ((dx, dy), axis) in enumerate(
        zip(_WIN_DIRECTIONS, axes, strict=True)
    ):
        for start in range(2, WIN_LENGTH + 1):
            end = start + 4
            window = axis[start:end]
            if (
                window.count(1) == 3
                and EMPTY in window
                and axis[start - 1] == axis[end] == EMPTY
                and axis[start - 2] != 1
                and axis[end + 1] != 1
            ):
                stones = tuple(index for index in range(start, end) if axis[index] == 1)
                offset = start + window.index(EMPTY) - WIN_LENGTH
                extension = Move(move.x + dx * offset, move.y + dy * offset)
                threes.setdefault((axis_index, stones), set()).add(extension)
    if len(threes) < 2:
        return False, None
    legal_threes = 0
    extensions: dict[Move, tuple[bool, ForbiddenMoveReason | None]] = {}
    for moves in threes.values():
        for extension in moves:
            if extension not in extensions:
                extensions[extension] = _evaluate_black_move(board, extension)
            if extensions[extension] == (False, None):
                legal_threes += 1
                break
        if legal_threes >= 2:
            return False, ForbiddenMoveReason.DOUBLE_THREE
    return False, None


def _evaluate_black_move(
    board: Board, move: Move
) -> tuple[bool, ForbiddenMoveReason | None]:
    board[move.y][move.x] = 1
    try:
        return _black_outcome(board, move)
    finally:
        board[move.y][move.x] = EMPTY


def _black_has_legal_move(board: Board) -> bool:
    return any(
        _evaluate_black_move(board, Move(x, y))[1] is None
        for y, row in enumerate(board)
        for x, cell in enumerate(row)
        if cell == EMPTY
    )


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

    policy = state.forbidden_move_policy
    foul = None
    result_reason = None
    if player == 1 and policy is not ForbiddenMovePolicy.OFF:
        won, foul = _black_outcome(board, move)
    else:
        won = has_won(board, move.x, move.y, player)

    if foul is not None:
        if policy is ForbiddenMovePolicy.WARN:
            raise ForbiddenMoveError(foul)
        status = GameStatus.WON
        winner = 2
        current_player = player
        result_reason = GameResultReason(foul.value)
    elif won:
        status = GameStatus.WON
        winner = player
        current_player = player
    elif all(cell != EMPTY for row in board for cell in row):
        status = GameStatus.DRAW
        winner = None
        current_player = player
    elif (
        player == 2
        and policy is ForbiddenMovePolicy.WARN
        and not _black_has_legal_move(board)
    ):
        status = GameStatus.WON
        winner = player
        current_player = player
        result_reason = GameResultReason.NO_LEGAL_BLACK_MOVE
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
        result_reason=result_reason,
    )


def select_cpu_move(
    board: Board, policy: ForbiddenMovePolicy = ForbiddenMovePolicy.OFF
) -> Move | None:
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
                black_wins = (
                    has_won(candidate_board, x, y, 1)
                    if policy is ForbiddenMovePolicy.OFF
                    else _black_exact_five(candidate_board, x, y)
                )
                if black_wins:
                    block = Move(x, y)
            candidate_board[y][x] = EMPTY
            distance = (x - center) ** 2 + (y - center) ** 2
            if distance < closest_distance:
                closest_distance = distance
                fallback = Move(x, y)
    if fallback is None:
        return block
    if policy is ForbiddenMovePolicy.WARN:
        for y, row in enumerate(board):
            for x, cell in enumerate(row):
                if cell != EMPTY:
                    continue
                candidate_board[y][x] = 2
                wins = any(
                    EMPTY in row for row in candidate_board
                ) and not _black_has_legal_move(candidate_board)
                candidate_board[y][x] = EMPTY
                if wins:
                    return Move(x, y)
    if block is not None:
        return block
    if policy is not ForbiddenMovePolicy.OFF:
        return _find_restricted_tactical_move(candidate_board) or fallback
    return _find_tactical_move(board) or fallback


def _black_exact_five(board: Board, x: int, y: int) -> bool:
    return any(
        _line_length(board, x, y, dx, dy, 1) == WIN_LENGTH for dx, dy in _WIN_DIRECTIONS
    )


def _move_at(position: int) -> Move:
    y, x = divmod(position, BOARD_SIZE)
    return Move(x, y)


def _exact_five_at(board: Board, position: int) -> bool:
    move = _move_at(position)
    # The line count includes the pivot even while that intersection is empty.
    return _black_exact_five(board, move.x, move.y)


def _legal_black_double_threats(
    board: Board,
    black_completions: dict[int, set[int]],
    white_wins: Collection[int],
    white_move: int,
) -> int:
    count = 0
    for reply, wins in black_completions.items():
        if reply == white_move or any(win != reply for win in white_wins):
            continue
        move = _move_at(reply)
        won, foul = _evaluate_black_move(board, move)
        if foul is not None or won:
            continue
        board[move.y][move.x] = 1
        try:
            if (
                sum(_exact_five_at(board, win) for win in wins if win != white_move)
                >= 2
            ):
                count += 1
        finally:
            board[move.y][move.x] = EMPTY
    return count


def _find_restricted_tactical_move(board: Board) -> Move | None:
    cells = [cell for row in board for cell in row]
    completions = _two_move_completions(cells)
    white_wins = completions[2]
    forced_win = min(_double_threats(white_wins), key=_center_priority, default=None)
    if forced_win is not None:
        return _move_at(forced_win)

    # Keep geometric candidates before checking legality. A white stone can
    # legalize a previously forbidden reply, but cannot create a black pattern.
    threats = _double_threats(completions[1])
    if not threats:
        return None

    best = None
    fewest = len(threats) + 1
    candidates = sorted(
        (position for position, cell in enumerate(cells) if cell == EMPTY),
        key=_center_priority,
    )
    for candidate in candidates:
        move = _move_at(candidate)
        wins = white_wins.get(candidate, ())
        board[move.y][move.x] = 2
        try:
            remaining = _legal_black_double_threats(board, threats, wins, candidate)
            if (
                remaining == 0
                and len(wins) == 1
                and _restricted_follow_up(board, next(iter(wins)))
            ):
                return move
        finally:
            board[move.y][move.x] = EMPTY
        if remaining < fewest:
            best, fewest = move, remaining
    return best


def _restricted_follow_up(board: Board, forced_block: int) -> bool:
    block = _move_at(forced_block)
    won, foul = _evaluate_black_move(board, block)
    if foul is not None:
        # Every legal alternative leaves the white winning point available.
        return True
    if won:
        return False

    board[block.y][block.x] = 1
    try:
        cells = [cell for row in board for cell in row]
        empty = [position for position, cell in enumerate(cells) if cell == EMPTY]
        if not empty:
            return True
        black_wins = [position for position in empty if _exact_five_at(board, position)]
        if len(black_wins) > 1:
            return False
        completions = _two_move_completions(cells)
        threats = _double_threats(completions[1])
        if not threats:
            return True
        for candidate in black_wins or empty:
            move = _move_at(candidate)
            board[move.y][move.x] = 2
            try:
                wins = completions[2].get(candidate, ())
                if not _legal_black_double_threats(board, threats, wins, candidate):
                    return True
            finally:
                board[move.y][move.x] = EMPTY
        return False
    finally:
        board[block.y][block.x] = EMPTY


def _find_tactical_move(board: Board) -> Move | None:
    """Find a forced win on white's next turn or minimize black's threats."""
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

    candidates = sorted(
        (position for position, cell in enumerate(cells) if cell == EMPTY),
        key=_center_priority,
    )
    best = candidates[0]
    fewest = len(threats)
    for candidate in candidates:
        replies = _remaining_threats(candidate, white_wins.get(candidate, ()), threats)
        # Candidates already follow the tie-break order, so a tie cannot improve best.
        remaining = sum(1 for _ in islice(replies, fewest))
        if remaining < fewest:
            best, fewest = candidate, remaining
            if fewest == 0:
                break
    y, x = divmod(best, BOARD_SIZE)
    return Move(x, y)


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
    return next(_remaining_threats(candidate, white_wins, threats), None) is None


def _remaining_threats(
    candidate: int, white_wins: Collection[int], threats: dict[int, set[int]]
) -> Iterator[int]:
    """Yield each black reply that still creates an unanswerable double threat."""
    return (
        reply
        for reply, black_wins in threats.items()
        if reply != candidate
        and (len(black_wins) > 2 or candidate not in black_wins)
        and all(win == reply for win in white_wins)
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
