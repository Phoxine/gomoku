import pytest

from app.domain.game.service.game_service import (
    apply_move,
    initialize_board,
    select_cpu_move,
)
from app.domain.game.state import (
    Board,
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


def position(
    black: tuple[tuple[int, int], ...] = (),
    white: tuple[tuple[int, int], ...] = (),
) -> Board:
    board = initialize_board()
    for x, y in black:
        board[y][x] = 1
    for x, y in white:
        board[y][x] = 2
    return board


def state(
    board: Board,
    policy: ForbiddenMovePolicy = ForbiddenMovePolicy.WARN,
    player: Player = 1,
) -> GameState:
    return GameState(
        board, player, GameStatus.IN_PROGRESS, forbidden_move_policy=policy
    )


@pytest.mark.parametrize(("dx", "dy"), [(1, 0), (0, 1), (1, 1), (1, -1)])
def test_enabled_black_requires_exact_five_in_each_direction(dx: int, dy: int) -> None:
    pivot = Move(7, 7)
    stones = tuple((7 + dx * step, 7 + dy * step) for step in range(1, 6))
    exact = apply_move(state(position(stones[:4])), pivot)
    assert exact.status is GameStatus.WON and exact.winner == 1

    board = position(stones)
    with pytest.raises(ForbiddenMoveError) as error:
        apply_move(state(board), pivot)
    assert error.value.reason is IllegalMoveReason.FORBIDDEN_MOVE
    assert error.value.forbidden_reason is ForbiddenMoveReason.OVERLINE
    assert board[7][7] == 0


@pytest.mark.parametrize("policy", list(ForbiddenMovePolicy))
def test_white_overline_is_a_win_and_edge_moves_are_allowed(
    policy: ForbiddenMovePolicy,
) -> None:
    board = position(white=tuple((14 - step, 14 - step) for step in range(1, 6)))
    edge = apply_move(state(board, policy), Move(0, 0))
    won = apply_move(edge, Move(14, 14))
    assert won.status is GameStatus.WON and won.winner == 2
    assert won.result_reason is None


@pytest.mark.parametrize(
    ("black", "white", "expected"),
    [
        (
            ((5, 7), (6, 7), (8, 7), (7, 5), (7, 6), (7, 8)),
            (),
            ForbiddenMoveReason.DOUBLE_FOUR,
        ),
        (
            ((5, 7), (6, 7), (8, 7), (7, 5), (7, 6), (7, 8)),
            ((4, 7), (7, 4)),
            ForbiddenMoveReason.DOUBLE_FOUR,
        ),
        (
            ((5, 7), (6, 7), (8, 7), (7, 6), (7, 8), (7, 10)),
            (),
            ForbiddenMoveReason.DOUBLE_FOUR,
        ),
        (
            ((4, 7), (6, 7), (8, 7), (10, 7)),
            (),
            ForbiddenMoveReason.DOUBLE_FOUR,
        ),
        (
            ((6, 7), (9, 7), (7, 6), (7, 8)),
            (),
            ForbiddenMoveReason.DOUBLE_THREE,
        ),
    ],
    ids=[
        "two-open-fours",
        "two-closed-fours",
        "open-and-gapped-four",
        "same-axis",
        "gapped-double-three",
    ],
)
def test_warn_rejects_distinct_formations_and_preserves_turn(
    black: tuple[tuple[int, int], ...],
    white: tuple[tuple[int, int], ...],
    expected: ForbiddenMoveReason,
) -> None:
    initial = state(position(black, white))
    saved = [row.copy() for row in initial.board]

    with pytest.raises(ForbiddenMoveError) as error:
        apply_move(initial, Move(7, 7))

    assert error.value.forbidden_reason is expected
    assert initial.board == saved
    assert initial.current_player == 1
    assert initial.revision == len(black) + len(white)
    assert apply_move(initial, Move(0, 0)).current_player == 2


@pytest.mark.parametrize(
    "black",
    [
        ((5, 7), (6, 7), (8, 7)),
        ((5, 7), (6, 7), (8, 7), (7, 6), (7, 8)),
    ],
    ids=["two-winning-ends-of-one-four", "four-three"],
)
def test_a_single_four_is_legal_even_with_two_winning_ends_or_a_three(
    black: tuple[tuple[int, int], ...],
) -> None:
    result = apply_move(state(position(black)), Move(7, 7))
    assert result.status is GameStatus.IN_PROGRESS and result.current_player == 2


def test_exact_five_takes_precedence_over_an_overline_on_another_axis() -> None:
    board = position(
        ((3, 7), (4, 7), (5, 7), (6, 7), (7, 4), (7, 5), (7, 6), (7, 8), (7, 9))
    )
    result = apply_move(state(board, ForbiddenMovePolicy.LOSS), Move(7, 7))
    assert result.status is GameStatus.WON and result.winner == 1
    assert result.result_reason is None


def test_off_keeps_black_overline_as_a_win_and_loss_records_the_foul_stone() -> None:
    board = position(tuple((x, 0) for x in range(9, 14)))
    move = Move(14, 0)
    off = apply_move(state(board, ForbiddenMovePolicy.OFF), move)
    losing = apply_move(state(board, ForbiddenMovePolicy.LOSS), move)
    assert off.winner == 1 and off.result_reason is None
    assert losing.status is GameStatus.WON and losing.winner == 2
    assert losing.current_player == 1
    assert losing.result_reason is GameResultReason.OVERLINE
    assert losing.board[0][14] == 1 and losing.revision == 6
    assert board[0][14] == 0
    with pytest.raises(IllegalMoveError) as error:
        apply_move(losing, Move(0, 0))
    assert error.value.reason is IllegalMoveReason.GAME_FINISHED


@pytest.mark.parametrize(
    ("extension_stones", "extension_foul"),
    [
        (((8, 4), (8, 5), (8, 6), (8, 8), (8, 9)), ForbiddenMoveReason.OVERLINE),
        (((8, 6), (8, 8), (9, 8)), ForbiddenMoveReason.DOUBLE_THREE),
    ],
    ids=["false-three-from-overline", "false-three-from-nested-double-three"],
)
def test_forbidden_extension_does_not_make_a_live_three(
    extension_stones: tuple[tuple[int, int], ...],
    extension_foul: ForbiddenMoveReason,
) -> None:
    # The horizontal three needs (8, 7) to become a straight four.
    board = position(((6, 7), (9, 7), (7, 6), (7, 8)) + extension_stones)
    result = apply_move(state(board), Move(7, 7))
    assert result.status is GameStatus.IN_PROGRESS
    assert result.current_player == 2
    with pytest.raises(ForbiddenMoveError) as error:
        apply_move(state(result.board), Move(8, 7))
    assert error.value.forbidden_reason is extension_foul


def test_board_edge_cannot_supply_a_second_winning_end_for_a_three() -> None:
    board = position(((0, 6), (0, 8), (1, 7), (2, 7)))
    result = apply_move(state(board), Move(0, 7))
    assert result.status is GameStatus.IN_PROGRESS
    assert result.current_player == 2


def nearly_full_board() -> Board:
    offsets = (0, 0, 1, 0, 1, 1)
    board = initialize_board()
    for y, row in enumerate(board):
        for x in range(len(row)):
            row[x] = 2 if (x + offsets[y % len(offsets)]) % 2 else 1
    board[7][8] = 2
    board[7][9:14] = [1] * 5
    board[7][14] = 0
    return board


def test_white_wins_when_every_remaining_black_move_is_forbidden_in_warn() -> None:
    board = nearly_full_board()
    board[2][0] = 0

    result = apply_move(state(board, player=2), Move(0, 2))

    assert result.status is GameStatus.WON and result.winner == 2
    assert result.result_reason is GameResultReason.NO_LEGAL_BLACK_MOVE
    assert result.current_player == 2
    assert result.board[7][14] == 0 and result.revision == 224
    assert board[2][0] == 0


def test_black_foul_at_last_intersection_takes_precedence_over_draw() -> None:
    board = nearly_full_board()
    result = apply_move(state(board, ForbiddenMovePolicy.LOSS), Move(14, 7))
    assert result.status is GameStatus.WON and result.winner == 2
    assert result.result_reason is GameResultReason.OVERLINE
    assert result.revision == 225


@pytest.mark.parametrize("policy", [ForbiddenMovePolicy.WARN, ForbiddenMovePolicy.LOSS])
def test_cpu_does_not_block_a_black_overline_as_an_immediate_win(
    policy: ForbiddenMovePolicy,
) -> None:
    board = position(((0, 0), (1, 0), (2, 0), (4, 0), (5, 0)), ((6, 0),))
    original = [row.copy() for row in board]

    assert select_cpu_move(board) == Move(3, 0)
    assert select_cpu_move(board, policy) == Move(7, 7)
    assert board == original


def test_cpu_avoids_white_move_that_makes_a_black_double_threat_legal() -> None:
    board = position(((6, 5), (8, 5), (9, 5), (7, 4), (7, 6), (7, 8)))
    reply = Move(7, 5)
    with pytest.raises(ForbiddenMoveError) as error:
        apply_move(state(board), reply)
    assert error.value.forbidden_reason is ForbiddenMoveReason.DOUBLE_FOUR

    centered = apply_move(state(board, player=2), Move(7, 7))
    black = apply_move(centered, reply)
    assert black.status is GameStatus.IN_PROGRESS
    for win in (Move(5, 5), Move(10, 5)):
        assert apply_move(state(black.board), win).winner == 1

    assert select_cpu_move(board, ForbiddenMovePolicy.WARN) == Move(6, 7)


def test_cpu_can_force_a_white_win_at_a_forbidden_black_block() -> None:
    board = position(
        black=(
            (0, 0),
            (1, 0),
            (2, 0),
            (4, 0),
            (5, 0),
            (3, 5),
            (9, 10),
            (10, 10),
            (11, 10),
        ),
        white=((6, 0), (3, 1), (3, 2), (3, 3)),
    )
    policy = ForbiddenMovePolicy.WARN
    forcing_move = select_cpu_move(board, policy)
    assert forcing_move == Move(3, 4)
    forced = apply_move(state(board, player=2), forcing_move)
    with pytest.raises(ForbiddenMoveError) as error:
        apply_move(forced, Move(3, 0))
    assert error.value.forbidden_reason is ForbiddenMoveReason.OVERLINE

    legal_reply = apply_move(forced, Move(12, 10))
    assert apply_move(legal_reply, Move(3, 0)).winner == 2
