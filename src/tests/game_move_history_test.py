"""Verify recorded and legacy game history against PostgreSQL."""

import subprocess
import sys


def test_move_history_reconstruction_and_legacy_suffix() -> None:
    # Isolate Django setup from the framework-independent tests.
    script = """
import os
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import django
django.setup()

from django.conf import settings
from django.db import connection
from django.test import Client

from app.domain.game.model.game import Game
from app.domain.game.model.game_move import GameMove
from app.domain.game.repository.game_repository import (
    GameNotFoundError,
    GameRepository,
    InconsistentGameHistoryError,
)
from app.domain.game.service import game_service
from app.domain.game.service.application_service import GameApplicationService
from app.domain.game.state import (
    GameMode, GameState, GameStatus, IllegalMoveError, IllegalMoveReason, Move,
)


def draw_moves() -> list[Move]:
    # This pattern has 113 black and 112 white positions and no winning line.
    black, white = [], []
    for y in range(15):
        for x in range(15):
            positions = black if (x + 2 * y) % 4 < 2 else white
            positions.append(Move(x, y))
    last_move = black.pop()
    moves = [move for pair in zip(black, white, strict=True) for move in pair]
    return [*moves, last_move]


def verify_reconstruction(
    mode: GameMode, moves: list[Move], status: GameStatus
) -> None:
    game_id, initial = service.create_game(mode)
    empty = repository.read_verified_history(game_id)
    assert empty.state == initial and empty.start_revision == 0 and not empty.moves

    # Supply the desired white moves through the CPU selector so the same
    # legal win and draw sequences exercise the CPU command path as well.
    with patch.object(game_service, "select_cpu_move", side_effect=moves[1::2]):
        for revision, move in enumerate(moves):
            if mode is GameMode.CPU and revision % 2:
                state = service.advance_cpu(game_id, expected_revision=revision)
            else:
                expected_revision = revision if mode is GameMode.CPU else None
                state = service.place_move(game_id, move, expected_revision)

    history = repository.read_verified_history(game_id)
    assert history.start_revision == 0 and len(history.moves) == len(moves)
    replay = initial
    for number, (recorded, expected) in enumerate(
        zip(history.moves, moves, strict=True), start=1
    ):
        assert recorded.move_number == number and recorded.move == expected
        assert recorded.player == replay.current_player
        replay = game_service.apply_move(replay, recorded.move)

    assert replay == state == history.state == service.get_game(game_id)
    assert state.status is status
    assert state.winner == (1 if status is GameStatus.WON else None)
    assert state.current_player == 1 and state.revision == len(moves)
    if mode is GameMode.CPU:
        assert service.advance_cpu(game_id, state.revision) == state
    else:
        with pytest.raises(IllegalMoveError) as error:
            service.place_move(game_id, Move(13, 12))
        assert error.value.reason is IllegalMoveReason.GAME_FINISHED
    assert repository.read_verified_history(game_id) == history


def verify_legacy_suffix() -> UUID:
    board = game_service.initialize_board()
    board[3][:12] = [1, 2] * 6
    game = Game.objects.create(board=board, history_start_revision=12)
    empty = repository.read_verified_history(game.id)
    assert empty.start_revision == empty.state.revision == 12 and not empty.moves
    moves = [Move(0, 0), Move(14, 14), Move(10, 10)]
    for move in moves:
        state = service.place_move(game.id, move)

    history = repository.read_verified_history(game.id)
    assert history.state == state and history.start_revision == 12
    assert [
        (recorded.move_number, recorded.move, recorded.player)
        for recorded in history.moves
    ] == [(13, moves[0], 1), (14, moves[1], 2), (15, moves[2], 1)]
    replay = GameState(board, 1, GameStatus.IN_PROGRESS)
    for recorded in history.moves:
        replay = game_service.apply_move(replay, recorded.move)
    assert replay == state
    beginning = [row.copy() for row in history.state.board]
    for recorded in history.moves:
        beginning[recorded.move.y][recorded.move.x] = 0
    assert beginning == board

    response = Client().get(f"/api/v1/games/{game.id}/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(game.id) and payload["revision"] == 15
    assert payload["board"] == state.board
    return game.id


def verify_history_errors(game_id: UUID) -> None:
    rows = GameMove.objects.filter(game_id=game_id)
    for number in (13, 14, 15):
        saved = rows.values("game_id", "move_number", "player", "x", "y").get(
            move_number=number
        )
        rows.filter(move_number=number).delete()
        with pytest.raises(InconsistentGameHistoryError):
            repository.read_verified_history(game_id)
        GameMove.objects.create(**saved)

    # Each corrupt fixture still satisfies the PostgreSQL range constraints.
    rows.filter(move_number=13).update(player=2)
    with pytest.raises(InconsistentGameHistoryError):
        repository.read_verified_history(game_id)
    rows.filter(move_number=13).update(player=1, x=1)
    with pytest.raises(InconsistentGameHistoryError):
        repository.read_verified_history(game_id)
    rows.filter(move_number=13).update(x=0)

    GameMove.objects.create(game_id=game_id, move_number=16, player=2, x=1, y=0)
    with pytest.raises(InconsistentGameHistoryError):
        repository.read_verified_history(game_id)
    rows.filter(move_number=16).delete()

    Game.objects.filter(pk=game_id).update(history_start_revision=16)
    with pytest.raises(InconsistentGameHistoryError):
        repository.read_verified_history(game_id)
    Game.objects.filter(pk=game_id).update(history_start_revision=12)

    rows.delete()
    with pytest.raises(InconsistentGameHistoryError):
        repository.read_verified_history(game_id)
    with pytest.raises(GameNotFoundError):
        repository.read_verified_history(uuid4())


def verify_finished_legacy_game() -> None:
    board = game_service.initialize_board()
    board[0][:5] = [1] * 5
    board[1][:4] = [2] * 4
    game = Game.objects.create(
        board=board, status=GameStatus.WON, winner=1, history_start_revision=9
    )
    history = repository.read_verified_history(game.id)
    assert history.state.status is GameStatus.WON
    assert history.start_revision == history.state.revision == 9 and not history.moves
    url = f"/api/v1/games/{game.id}/"
    client = Client()
    response = client.get(url)
    assert response.status_code == 200 and response.json()["status"] == "won"
    response = client.post(
        f"{url}moves/", {"x": 14, "y": 14}, content_type="application/json"
    )
    assert response.status_code == 409 and response.json()["error"] == "game_finished"
    assert repository.read_verified_history(game.id) == history


settings.ALLOWED_HOSTS = ["testserver"]
connection.settings_dict["TEST"]["NAME"] = "gomoku_test_" + uuid4().hex
old_name = connection.settings_dict["NAME"]
connection.creation.create_test_db(verbosity=0)
try:
    service = GameApplicationService()
    repository = GameRepository()
    win = [Move(x, y) for x in range(4) for y in (0, 14)] + [Move(4, 0)]
    for mode in GameMode:
        verify_reconstruction(mode, win, GameStatus.WON)
        verify_reconstruction(mode, draw_moves(), GameStatus.DRAW)
    verify_history_errors(verify_legacy_suffix())
    verify_finished_legacy_game()
finally:
    connection.creation.destroy_test_db(old_name, verbosity=0)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
