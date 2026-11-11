import pytest

from app.services.game_service import (
    BOARD_SIZE,
    EMPTY,
    has_won,
    initialize_board,
    place_stone,
    validate_move,
)


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
    with pytest.raises(ValueError, match="between 0 and 14"):
        validate_move(initialize_board(), x, y, 1)


@pytest.mark.parametrize("x,y", [(1.5, 2), (2, "3")])
def test_validate_move_rejects_non_integer_coordinates(x: int, y: int) -> None:
    with pytest.raises(TypeError, match="integers"):
        validate_move(initialize_board(), x, y, 1)


def test_validate_move_rejects_occupied_position() -> None:
    board = initialize_board()
    board[4][7] = 1

    with pytest.raises(ValueError, match="already occupied"):
        validate_move(board, 7, 4, 2)


def test_validate_move_rejects_invalid_player() -> None:
    with pytest.raises(ValueError, match="Player"):
        validate_move(initialize_board(), 0, 0, 3)


def test_validate_move_rejects_malformed_board() -> None:
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
    board = initialize_board()
    for step in range(1, 5):
        board[7 - dy * step][7 - dx * step] = 1

    assert place_stone(board, 7, 7, 1) is True


def test_has_won_does_not_count_opponent_stones() -> None:
    board = initialize_board()
    for x in range(4):
        board[0][x] = 1
    board[0][4] = 2

    assert has_won(board, 3, 0, 1) is False


def test_has_won_recognizes_six_or_more_consecutive_stones() -> None:
    board = initialize_board()
    for x in range(2, 8):
        board[7][x] = 2

    assert has_won(board, 4, 7, 2) is True
