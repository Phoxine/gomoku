"""Verify forbidden-move API outcomes and persistence on PostgreSQL."""

import subprocess
import sys


def test_forbidden_move_policy_api_and_history() -> None:
    # Keep Django settings and the disposable database out of domain tests.
    script = """
import os
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import django
django.setup()

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from app.domain.game.model.game import Game
from app.domain.game.model.game_move import GameMove
from app.domain.game.repository.game_repository import GameRepository
from app.domain.game.service import game_service
from app.domain.game.state import GameMode, GameState, GameStatus, Move

settings.ALLOWED_HOSTS = ["testserver"]
settings.CPU_CREATION_ENABLED = True
connection.settings_dict["TEST"]["NAME"] = "gomoku_test_" + uuid4().hex
old_name = connection.settings_dict["NAME"]
client = Client()
repository = GameRepository()
games_url = "/api/v1/games/"


def post(url, data):
    return client.post(url, data, content_type="application/json")


def assert_error(response, status, error, **fields):
    assert response.status_code == status
    assert response.json() == {"error": error, **fields}


def verify_migration():
    old_target = [("game", "0003_game_move_history")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    old_game = executor.loader.project_state(old_target).apps.get_model("game", "Game")
    active = old_game.objects.create()
    board = game_service.initialize_board()
    board[0][0:5] = [1] * 5
    completed = old_game.objects.create(
        board=board, status="won", winner=1, history_start_revision=5
    )

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes("game"))
    for previous in (active, completed):
        migrated = Game.objects.get(pk=previous.pk)
        assert migrated.forbidden_move_policy == "off"
        assert migrated.result_reason is None
        assert migrated.board == previous.board and migrated.status == previous.status
        assert migrated.winner == previous.winner
        assert migrated.history_start_revision == previous.history_start_revision
        assert migrated.created_at == previous.created_at
        assert migrated.updated_at == previous.updated_at
        assert not migrated.moves.exists()
    overlapping_writer = old_game.objects.create()
    assert Game.objects.get(pk=overlapping_writer.pk).forbidden_move_policy == "off"

    white_win = {"status": "won", "winner": 2}
    for invalid in (
        {"forbidden_move_policy": "bad"},
        {"forbidden_move_policy": "loss", "result_reason": "overline"},
        white_win | {"forbidden_move_policy": "warn", "result_reason": "double_four"},
        white_win | {
            "forbidden_move_policy": "loss", "result_reason": "no_legal_black_move",
        },
        white_win | {"forbidden_move_policy": "loss", "result_reason": "bad"},
        {
            "forbidden_move_policy": "loss", "result_reason": "double_three",
            "status": "won", "winner": 2, "current_player": 2,
        },
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            Game.objects.create(**invalid)


def verify_create():
    for response in (client.post(games_url), post(games_url, {})):
        assert response.status_code == 201
        assert response.json()["forbidden_move_policy"] == "off"
        assert response.json()["result_reason"] is None
    for value in (None, True, 1, {}, [], "renju"):
        assert_error(
            post(games_url, {"forbidden_move_policy": value}),
            400, "invalid_forbidden_move_policy",
        )


def prepare_overline(mode, policy):
    response = post(games_url, {"mode": mode.value, "forbidden_move_policy": policy})
    assert response.status_code == 201
    initial = response.json()
    assert initial["mode"] == mode.value
    assert initial["forbidden_move_policy"] == policy
    assert initial["result_reason"] is None
    game_id = UUID(initial["id"])
    game_url = f"{games_url}{game_id}/"
    cpu = mode is GameMode.CPU
    white_moves = [Move(x, 14) for x in (0, 2, 4, 6, 8)]
    with patch.object(game_service, "select_cpu_move", side_effect=white_moves):
        pairs = zip((1, 2, 3, 5, 6), white_moves, strict=True)
        for index, (black_x, white) in enumerate(pairs):
            payload = {"x": black_x, "y": 0}
            if cpu:
                payload["expected_revision"] = 2 * index
            assert post(game_url + "moves/", payload).status_code == 200
            if cpu:
                reply = post(
                    game_url + "cpu-move/", {"expected_revision": 2 * index + 1}
                )
            else:
                reply = post(game_url + "moves/", {"x": white.x, "y": white.y})
            assert reply.status_code == 200
    assert reply.json()["revision"] == 10
    return game_id, game_url


def verify_forbidden_move(mode, policy):
    cpu = mode is GameMode.CPU
    game_id, game_url = prepare_overline(mode, policy)
    before_history = repository.read_verified_history(game_id)
    before_response = client.get(game_url).json()
    payload = {"x": 4, "y": 0}
    if cpu:
        payload["expected_revision"] = 10
        assert_error(
            post(game_url + "moves/", payload | {"expected_revision": 8}),
            409, "stale_revision",
        )
        assert repository.read_verified_history(game_id) == before_history

    if policy == "loss":
        with patch.object(
            GameMove.objects, "create", side_effect=IntegrityError("insert failed")
        ):
            with pytest.raises(IntegrityError):
                post(game_url + "moves/", payload)
        assert client.get(game_url).json() == before_response
        assert repository.read_verified_history(game_id) == before_history

    response = post(game_url + "moves/", payload)
    if policy == "warn":
        assert_error(response, 409, "forbidden_move", reason="overline")
        assert client.get(game_url).json() == before_response
        assert repository.read_verified_history(game_id) == before_history
        if cpu:
            reply = post(game_url + "cpu-move/", {"expected_revision": 10})
            assert reply.status_code == 200 and reply.json() == before_response
        retry = post(game_url + "moves/", payload | {"x": 14})
        assert retry.status_code == 200
        assert retry.json()["board"][0][14] == 1 and retry.json()["revision"] == 11
        assert retry.json()["status"] == "in_progress"
        return

    assert response.status_code == 200
    final = response.json()
    assert final["board"][0][4] == 1 and final["revision"] == 11
    assert final["status"] == "won" and final["current_player"] == 1
    assert final["winner"] == (2 if policy == "loss" else 1)
    assert final["result_reason"] == ("overline" if policy == "loss" else None)
    assert client.get(game_url).json() == final
    assert_error(post(game_url + "moves/", payload), 409, "game_finished")
    if cpu:
        reply = post(game_url + "cpu-move/", {"expected_revision": 11})
        assert reply.status_code == 200 and reply.json() == final
    after = repository.read_verified_history(game_id)
    assert after.moves[:-1] == before_history.moves
    last = after.moves[-1]
    assert (last.move_number, last.player, last.move) == (11, 1, Move(4, 0))
    replay = GameState(
        game_service.initialize_board(), 1, GameStatus.IN_PROGRESS,
        mode=mode, forbidden_move_policy=after.state.forbidden_move_policy,
    )
    for entry in after.moves:
        replay = game_service.apply_move(replay, entry.move)
    assert replay == after.state


def verify_no_legal_black_move(mode):
    board = [[1 if (x + 2 * y) % 4 < 2 else 2 for x in range(15)] for y in range(15)]
    board[0][1:7] = [1, 1, 1, 0, 1, 1]
    board[14][14] = 0
    game_id = Game.objects.create(
        board=board, current_player=2, mode=mode.value,
        forbidden_move_policy="warn", history_start_revision=223,
    ).pk
    game_url = f"{games_url}{game_id}/"
    if mode is GameMode.CPU:
        response = post(game_url + "cpu-move/", {"expected_revision": 223})
    else:
        response = post(game_url + "moves/", {"x": 14, "y": 14})
    assert response.status_code == 200
    final = response.json()
    assert final["board"][0][4] == 0 and final["board"][14][14] == 2
    assert final["revision"] == 224 and final["current_player"] == 2
    assert final["status"] == "won" and final["winner"] == 2
    assert final["result_reason"] == "no_legal_black_move"
    assert client.get(game_url).json() == final
    history = repository.read_verified_history(game_id)
    assert history.start_revision == 223
    [(number, player, move)] = [
        (entry.move_number, entry.player, entry.move) for entry in history.moves
    ]
    assert (number, player, move) == (224, 2, Move(14, 14))


# Start without Django's automatic migration to head to test existing records.
with patch("django.core.management.call_command"):
    connection.creation.create_test_db(verbosity=0)
try:
    verify_migration()
    verify_create()
    for mode in GameMode:
        for policy in ("off", "warn", "loss"):
            verify_forbidden_move(mode, policy)
        verify_no_legal_black_move(mode)
finally:
    connection.creation.destroy_test_db(old_name, verbosity=0)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
