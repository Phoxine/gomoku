"""Isolated tests for game application service orchestration."""

from contextlib import nullcontext
from types import ModuleType
from unittest.mock import Mock, patch
from uuid import uuid4

import django
import pytest
from django.conf import settings

from app.domain.game.service.game_service import initialize_board
from app.domain.game.state import (
    GameMode,
    GameState,
    GameStatus,
    IllegalMoveError,
    IllegalMoveReason,
    Move,
    Player,
)


@pytest.fixture
def service_module() -> ModuleType:
    if not settings.configured:
        settings.configure(SECRET_KEY="test", INSTALLED_APPS=["app.domain.game"])
        django.setup()
    from app.domain.game.service import application_service

    return application_service


def test_create_game_initializes_and_returns_repository_result(
    service_module: ModuleType,
) -> None:
    repository = Mock()
    result = (uuid4(), GameState(initialize_board(), 1, GameStatus.IN_PROGRESS))
    repository.create.return_value = result

    assert service_module.GameApplicationService(repository).create_game() == result
    repository.create.assert_called_once_with(result[1])


def test_get_game_returns_repository_state(service_module: ModuleType) -> None:
    repository = Mock()
    game_id = uuid4()
    state = GameState(initialize_board(), 1, GameStatus.IN_PROGRESS)
    repository.get.return_value = state

    assert service_module.GameApplicationService(repository).get_game(game_id) is state
    repository.get.assert_called_once_with(game_id)


def test_place_move_locks_and_saves_transition_inside_transaction(
    service_module: ModuleType,
) -> None:
    repository = Mock()
    game_id = uuid4()
    state = GameState(initialize_board(), 1, GameStatus.IN_PROGRESS)
    repository.get_for_update.return_value = state
    repository.save.side_effect = lambda game_id, updated: updated
    transaction = Mock()
    transaction.attach_mock(repository, "repository")
    transaction.atomic.return_value = nullcontext()

    with patch.object(service_module.transaction, "atomic", transaction.atomic):
        result = service_module.GameApplicationService(repository).place_move(
            game_id, Move(3, 4)
        )

    assert result.board[4][3] == 1
    assert result.current_player == 2
    assert state.board[4][3] == 0
    assert transaction.mock_calls == [
        ("atomic", (), {}),
        ("repository.get_for_update", (game_id,), {}),
        ("repository.save", (game_id, result), {}),
    ]


def test_place_move_does_not_save_illegal_move(service_module: ModuleType) -> None:
    repository = Mock()
    board = initialize_board()
    board[4][3] = 1
    repository.get_for_update.return_value = GameState(board, 2, GameStatus.IN_PROGRESS)

    with patch.object(service_module.transaction, "atomic", return_value=nullcontext()):
        with pytest.raises(IllegalMoveError):
            service_module.GameApplicationService(repository).place_move(
                uuid4(), Move(3, 4)
            )

    repository.save.assert_not_called()


def test_advance_cpu_locks_and_saves_only_the_selected_move(
    service_module: ModuleType,
) -> None:
    repository = Mock()
    game_id = uuid4()
    board = initialize_board()
    board[0][0] = 1
    state = GameState(board, 2, GameStatus.IN_PROGRESS, mode=GameMode.CPU)
    repository.get_for_update.return_value = state
    repository.save.side_effect = lambda game_id, updated: updated
    transaction = Mock()
    transaction.attach_mock(repository, "repository")
    transaction.atomic.return_value = nullcontext()

    with patch.object(service_module.transaction, "atomic", transaction.atomic):
        result = service_module.GameApplicationService(repository).advance_cpu(
            game_id, 1
        )

    assert result.revision == 2 and result.current_player == 1
    assert result.board[7][7] == 2 and state.board[7][7] == 0
    assert transaction.mock_calls == [
        ("atomic", (), {}),
        ("repository.get_for_update", (game_id,), {}),
        ("repository.save", (game_id, result), {}),
    ]


@pytest.mark.parametrize(
    ("current_player", "status", "expected_revision"),
    [
        (1, GameStatus.IN_PROGRESS, 2),
        (2, GameStatus.IN_PROGRESS, 0),
        (2, GameStatus.WON, 10),
    ],
)
def test_advance_cpu_skips_selection_and_persistence_when_ineligible(
    service_module: ModuleType,
    current_player: Player,
    status: GameStatus,
    expected_revision: int,
) -> None:
    repository = Mock()
    board = initialize_board()
    if status is GameStatus.WON:
        board[0][:5] = [2] * 5
        board[1][:9:2] = [1] * 5
    else:
        board[0][0] = 1
        if current_player == 1:
            board[7][7] = 2
    state = GameState(
        board,
        current_player,
        status,
        winner=2 if status is GameStatus.WON else None,
        mode=GameMode.CPU,
    )
    repository.get_for_update.return_value = state

    with (
        patch.object(service_module.transaction, "atomic", return_value=nullcontext()),
        patch.object(service_module.game_service, "select_cpu_move") as select,
    ):
        result = service_module.GameApplicationService(repository).advance_cpu(
            uuid4(), expected_revision
        )

    assert result is state
    select.assert_not_called()
    repository.save.assert_not_called()


def test_advance_cpu_rejects_two_player_games(service_module: ModuleType) -> None:
    repository = Mock()
    repository.get_for_update.return_value = GameState(
        initialize_board(), 1, GameStatus.IN_PROGRESS
    )

    with (
        patch.object(service_module.transaction, "atomic", return_value=nullcontext()),
        pytest.raises(IllegalMoveError) as error,
    ):
        service_module.GameApplicationService(repository).advance_cpu(uuid4(), 0)

    assert error.value.reason is IllegalMoveReason.NOT_CPU_GAME
    repository.save.assert_not_called()
