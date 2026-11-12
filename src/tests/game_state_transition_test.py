import pytest

from app.domain.game.service.game_service import apply_move, initialize_board
from app.domain.game.state import (
    GameState,
    GameStatus,
    IllegalMoveError,
    IllegalMoveReason,
    Move,
)


def make_state(
    board: list[list[int]] | None = None,
    current_player: int = 1,
    status: GameStatus = GameStatus.IN_PROGRESS,
    winner: int | None = None,
) -> GameState:
    return GameState(
        board=initialize_board() if board is None else board,
        current_player=current_player,
        status=status,
        winner=winner,
    )


def test_apply_move_places_stone_at_board_edges_and_alternates_turns() -> None:
    initial_state = make_state()

    first_result = apply_move(initial_state, Move(x=0, y=0))
    second_result = apply_move(first_result, Move(x=14, y=14))

    assert first_result.board[0][0] == 1
    assert first_result.current_player == 2
    assert first_result.status is GameStatus.IN_PROGRESS
    assert first_result.winner is None
    assert second_result.board[14][14] == 2
    assert second_result.current_player == 1
    assert second_result.status is GameStatus.IN_PROGRESS


def test_apply_move_returns_a_new_state_without_mutating_input_board() -> None:
    state = make_state()
    original_board = [row.copy() for row in state.board]

    result = apply_move(state, Move(x=4, y=6))

    assert state.board == original_board
    assert result.board[6][4] == 1
    assert result.board is not state.board
    assert all(
        result_row is not original_row
        for result_row, original_row in zip(result.board, state.board, strict=True)
    )


@pytest.mark.parametrize(
    ("dx", "dy"),
    [(1, 0), (0, 1), (1, 1), (1, -1)],
)
def test_apply_move_detects_wins_in_all_four_directions(dx: int, dy: int) -> None:
    board = initialize_board()
    for step in range(1, 5):
        board[7 - dy * step][7 - dx * step] = 1
    state = make_state(board=board)

    result = apply_move(state, Move(x=7, y=7))

    assert result.status is GameStatus.WON
    assert result.winner == 1
    assert result.current_player == 1
    assert state.board[7][7] == 0


def test_apply_move_marks_a_full_non_winning_board_as_draw() -> None:
    board = initialize_board()
    row_offsets = (0, 0, 1, 0, 1, 1)
    for y, row in enumerate(board):
        offset = row_offsets[y % len(row_offsets)]
        for x in range(len(row)):
            row[x] = 1 + ((x + offset) % 2)

    x = y = 14
    final_player = board[y][x]
    board[y][x] = 0
    state = make_state(board=board, current_player=final_player)

    result = apply_move(state, Move(x=x, y=y))

    assert result.status is GameStatus.DRAW
    assert result.winner is None
    assert result.current_player == final_player
    assert all(cell != 0 for row in result.board for cell in row)
    assert state.board[y][x] == 0


def test_apply_move_reports_win_when_final_cell_also_fills_the_board() -> None:
    board = initialize_board()
    row_offsets = (0, 0, 1, 0, 1, 1)
    for y, row in enumerate(board):
        offset = row_offsets[y % len(row_offsets)]
        for x in range(len(row)):
            row[x] = 1 + ((x + offset) % 2)
    y = 7
    for x in range(10, 14):
        board[y][x] = 1
    board[y][14] = 0

    result = apply_move(make_state(board=board), Move(x=14, y=y))

    assert result.status is GameStatus.WON
    assert result.winner == 1
    assert all(cell != 0 for row in result.board for cell in row)


@pytest.mark.parametrize(
    ("move", "reason"),
    [
        (Move(x=1.5, y=0), IllegalMoveReason.INVALID_COORDINATE),
        (Move(x=0, y="1"), IllegalMoveReason.INVALID_COORDINATE),
        (Move(x=True, y=0), IllegalMoveReason.INVALID_COORDINATE),
        (Move(x=0, y=False), IllegalMoveReason.INVALID_COORDINATE),
        (Move(x=-1, y=0), IllegalMoveReason.OUT_OF_BOUNDS),
        (Move(x=0, y=15), IllegalMoveReason.OUT_OF_BOUNDS),
    ],
)
def test_apply_move_reports_coordinate_errors_with_reason_codes(
    move: Move,
    reason: IllegalMoveReason,
) -> None:
    with pytest.raises(IllegalMoveError) as error:
        apply_move(make_state(), move)

    assert error.value.reason is reason


def test_apply_move_rejects_an_occupied_position() -> None:
    board = initialize_board()
    board[3][8] = 2

    with pytest.raises(IllegalMoveError) as error:
        apply_move(make_state(board=board), Move(x=8, y=3))

    assert error.value.reason is IllegalMoveReason.OCCUPIED


@pytest.mark.parametrize(
    ("status", "winner"),
    [(GameStatus.WON, 1), (GameStatus.DRAW, None)],
)
def test_apply_move_rejects_moves_after_the_game_finishes(
    status: GameStatus,
    winner: int | None,
) -> None:
    state = make_state(status=status, winner=winner)

    with pytest.raises(IllegalMoveError) as error:
        apply_move(state, Move(x=0, y=0))

    assert error.value.reason is IllegalMoveReason.GAME_FINISHED
    assert state.board[0][0] == 0


def test_apply_move_rejects_a_malformed_finished_state() -> None:
    state = make_state(status=GameStatus.WON)

    with pytest.raises(ValueError, match="valid winner"):
        apply_move(state, Move(x=0, y=0))
