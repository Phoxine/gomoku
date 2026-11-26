import pytest

from app.domain.game.service.game_service import (
    BOARD_SIZE,
    EMPTY,
    has_won,
    initialize_board,
    place_stone,
    select_cpu_move,
    validate_move,
)
from app.domain.game.state import Board, Move, Player


def test_initialize_board_returns_empty_15_by_15_board() -> None:
    board = initialize_board()

    assert len(board) == BOARD_SIZE
    assert all(len(row) == BOARD_SIZE for row in board)
    assert all(cell == EMPTY for row in board for cell in row)


@pytest.mark.parametrize("x,y", [(0, 0), (14, 14), (0, 14), (14, 0)])
def test_validate_move_accepts_empty_board_edges(x: int, y: int) -> None:
    validate_move(initialize_board(), x, y, 1)


@pytest.mark.parametrize("x,y", [(-1, 0), (0, -1), (15, 0), (0, 15)])
def test_validate_move_rejects_out_of_bounds_coordinates(x: int, y: int) -> None:
    """Reject coordinates outside the board bounds."""
    with pytest.raises(ValueError, match="between 0 and 14"):
        validate_move(initialize_board(), x, y, 1)


@pytest.mark.parametrize("x,y", [(1.5, 2), (2, "3"), (True, 2), (2, False)])
def test_validate_move_rejects_non_integer_coordinates(x: int, y: int) -> None:
    """Reject coordinate values that are not integers."""
    with pytest.raises(TypeError, match="integers"):
        validate_move(initialize_board(), x, y, 1)


def test_validate_move_rejects_occupied_position() -> None:
    """Reject a move that targets an occupied cell."""
    board = initialize_board()
    board[4][7] = 1

    with pytest.raises(ValueError, match="already occupied"):
        validate_move(board, 7, 4, 2)


def test_validate_move_rejects_invalid_player() -> None:
    """Reject player identifiers outside the supported range."""
    with pytest.raises(ValueError, match="Player"):
        validate_move(initialize_board(), 0, 0, 3)


@pytest.mark.parametrize("player", [True, False, 1.0, 2.0])
def test_place_stone_rejects_non_integer_player_without_mutation(
    player: object,
) -> None:
    board = initialize_board()

    with pytest.raises(ValueError, match="Player"):
        place_stone(board, 0, 0, player)

    assert board == initialize_board()


def test_validate_move_rejects_malformed_board() -> None:
    """Reject boards that do not have the required dimensions."""
    with pytest.raises(ValueError, match="15 by 15"):
        validate_move([[EMPTY]], 0, 0, 1)


def test_place_stone_updates_board_and_returns_false_before_win() -> None:
    board = initialize_board()

    assert place_stone(board, 3, 5, 1) is False
    assert board[5][3] == 1


@pytest.mark.parametrize(
    "dx,dy",
    [(1, 0), (0, 1), (1, 1), (1, -1)],
)
def test_place_stone_detects_win_in_all_four_directions(
    dx: int,
    dy: int,
) -> None:
    """Detect a winning move along each supported direction."""
    board = initialize_board()
    for step in range(1, 5):
        board[7 - dy * step][7 - dx * step] = 1

    assert place_stone(board, 7, 7, 1) is True


def test_has_won_does_not_count_opponent_stones() -> None:
    """Ensure stones belonging to the opponent break a winning line."""
    board = initialize_board()
    for x in range(4):
        board[0][x] = 1
    board[0][4] = 2

    assert has_won(board, 3, 0, 1) is False


def test_has_won_recognizes_six_or_more_consecutive_stones() -> None:
    """Treat a line longer than five stones as a win."""
    board = initialize_board()
    for x in range(2, 8):
        board[7][x] = 2

    assert has_won(board, 4, 7, 2) is True


def test_cpu_takes_a_win_before_blocking_an_earlier_threat() -> None:
    board = initialize_board()
    board[0][:4] = [1, 1, 1, 1]
    board[14][11:] = [2, 2, 2, 2]
    original = [row.copy() for row in board]

    assert select_cpu_move(board) == Move(10, 14)
    assert board == original


def test_cpu_blocks_the_first_winning_black_move_in_board_order() -> None:
    board = initialize_board()
    board[0][1:5] = [1, 1, 1, 1]
    board[1][:4] = [1, 1, 1, 1]

    assert select_cpu_move(board) == Move(0, 0)


def test_cpu_blocks_a_single_immediate_black_win_before_defending_elsewhere() -> None:
    board = initialize_board()
    board[0][:4] = [1, 1, 1, 1]
    board[7][4:7] = [1, 1, 1]

    assert select_cpu_move(board) == Move(4, 0)


def test_cpu_defends_before_black_can_create_two_winning_moves() -> None:
    board = initialize_board()
    for x, y, player in [(7, 6, 1), (7, 7, 2), (6, 7, 1), (8, 7, 2), (5, 8, 1)]:
        place_stone(board, x, y, player)
    original = [row.copy() for row in board]

    assert select_cpu_move(board) == Move(8, 5)
    assert board == original

    assert _black_has_forcing_reply(board)
    board[5][8] = 2
    assert not _black_has_forcing_reply(board)


def _winning_moves(board: Board, player: Player) -> set[Move]:
    wins = set()
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            if cell != EMPTY:
                continue
            board[y][x] = player
            if has_won(board, x, y, player):
                wins.add(Move(x, y))
            board[y][x] = EMPTY
    return wins


def _black_has_forcing_reply(board: Board) -> bool:
    """Simulate every black reply without using the selector's window pruning."""
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            if cell != EMPTY:
                continue
            board[y][x] = 1
            forces_win = len(_winning_moves(board, 1)) >= 2 and not _winning_moves(
                board, 2
            )
            board[y][x] = EMPTY
            if forces_win:
                return True
    return False


@pytest.mark.parametrize(
    "black,white,expected",
    [
        pytest.param([(4, 7), (5, 7), (7, 7)], [], Move(6, 7), id="gapped-row-tie"),
        pytest.param(
            [(2, 4), (3, 4), (6, 4), (4, 1), (4, 2), (4, 5)],
            [],
            Move(5, 4),
            id="crossing",
        ),
        pytest.param(
            [(2, 1), (3, 1), (5, 1)],
            [(4, 7), (5, 7), (6, 7)],
            Move(7, 7),
            id="white-counter-win",
        ),
    ],
)
def test_cpu_defenses_agree_with_reply_simulation(
    black: list[tuple[int, int]], white: list[tuple[int, int]], expected: Move
) -> None:
    board = initialize_board()
    for x, y in black:
        board[y][x] = 1
    for x, y in white:
        board[y][x] = 2

    assert not _winning_moves(board, 1)
    assert not _winning_moves(board, 2)
    assert _black_has_forcing_reply(board)
    assert select_cpu_move(board) == expected
    board[expected.y][expected.x] = 2
    assert not _black_has_forcing_reply(board)


def test_cpu_does_not_count_one_winning_move_twice_for_overlapping_lines() -> None:
    board = initialize_board()
    board[0][:8] = [0, 2, 1, 1, 0, 1, 0, 1]
    board[0][4] = 1
    assert _winning_moves(board, 1) == {Move(6, 0)}
    board[0][4] = EMPTY

    assert not _black_has_forcing_reply(board)
    assert select_cpu_move(board) == Move(7, 7)


def test_cpu_uses_center_fallback_when_no_defense_blocks_both_threats() -> None:
    board = initialize_board()
    for y in (1, 13):
        board[y][2:6] = [1, 1, 0, 1]

    assert not _winning_moves(board, 1)
    assert _black_has_forcing_reply(board)
    assert select_cpu_move(board) == Move(7, 7)


def test_cpu_fallback_prefers_center_and_breaks_distance_ties_by_row_then_column() -> (
    None
):
    board = initialize_board()

    assert select_cpu_move(board) == Move(7, 7)
    board[7][7] = 1
    assert select_cpu_move(board) == Move(7, 6)
    board[6][7] = 2
    assert select_cpu_move(board) == Move(6, 7)


def test_cpu_selects_the_only_empty_intersection_and_handles_a_full_board() -> None:
    board = [[1 if (x + 2 * y) % 4 < 2 else 2 for x in range(15)] for y in range(15)]
    board[14][14] = 0

    assert select_cpu_move(board) == Move(14, 14)
    board[14][14] = 2
    assert select_cpu_move(board) is None


def test_validate_board_rejects_invalid_shapes_and_cells() -> None:
    from app.domain.game.service.game_service import initialize_board, validate_board

    validate_board(initialize_board())
    invalid_cell = initialize_board()
    invalid_cell[0][0] = 3
    boolean_cell = initialize_board()
    boolean_cell[0][0] = True
    for board in (None, [], [[0] * 15] * 14, invalid_cell, boolean_cell):
        with pytest.raises(ValueError):
            validate_board(board)
