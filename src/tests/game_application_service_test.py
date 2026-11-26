"""Exercise persistence, transaction rollback, and serialized move commands."""

import subprocess
import sys


def test_game_application_service_with_postgres() -> None:
    # A separate process configures Django without imposing global settings on
    # the framework-independent unit tests in this suite.
    script = """
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from django.conf import settings
url = urlparse(os.environ["DATABASE_URL"])
settings.configure(
    SECRET_KEY="test",
    INSTALLED_APPS=["app.domain.game"],
    DATABASES={"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": unquote(url.path[1:]),
        "USER": unquote(url.username or ""), "PASSWORD": unquote(url.password or ""),
        "HOST": url.hostname, "PORT": url.port or 5432,
        "TEST": {"NAME": "gomoku_test_" + uuid.uuid4().hex},
    }},
    USE_TZ=True,
)
import django
django.setup()
from django.core.management import call_command
from django.db import close_old_connections, connection
from app.domain.game.repository.game_repository import GameNotFoundError, GameRepository
from app.domain.game.service import game_service
from app.domain.game.service.application_service import GameApplicationService
from app.domain.game.service.game_service import initialize_board
from app.domain.game.state import (
    GameMode, GameState, GameStatus, IllegalMoveError, IllegalMoveReason, Move,
)

old_name = connection.settings_dict["NAME"]
connection.creation.create_test_db(verbosity=0)
try:
    call_command("migrate", verbosity=0)
    repo = GameRepository()
    service = GameApplicationService()
    game_id, initial = service.create_game()
    assert initial == GameState(initialize_board(), 1, GameStatus.IN_PROGRESS)
    assert service.get_game(game_id) == initial
    moved = service.place_move(game_id, Move(3, 4))
    assert moved.board[4][3] == 1 and moved.current_player == 2
    assert service.get_game(game_id) == moved
    assert initial.board[4][3] == 0

    for move, reason in [
        (Move(True, 1), IllegalMoveReason.INVALID_COORDINATE),
        (Move(-1, 1), IllegalMoveReason.OUT_OF_BOUNDS),
        (Move(3, 4), IllegalMoveReason.OCCUPIED),
    ]:
        try:
            service.place_move(game_id, move)
        except IllegalMoveError as exc:
            assert exc.reason == reason
        else:
            raise AssertionError("illegal move accepted")
        assert service.get_game(game_id) == moved

    missing = uuid.uuid4()
    for call in (
        lambda: service.get_game(missing),
        lambda: service.place_move(missing, Move(0, 0)),
    ):
        try:
            call()
        except GameNotFoundError:
            pass
        else:
            raise AssertionError("missing game accepted")

    board = initialize_board()
    board[0][:4] = [1, 1, 1, 1]
    repo.save(game_id, GameState(board, 1, GameStatus.IN_PROGRESS))
    won = service.place_move(game_id, Move(4, 0))
    assert won.status == GameStatus.WON and won.winner == 1
    assert service.get_game(game_id) == won
    try:
        service.place_move(game_id, Move(5, 0))
    except IllegalMoveError as exc:
        assert exc.reason == IllegalMoveReason.GAME_FINISHED
    else:
        raise AssertionError("move after win accepted")

    # A full board with no line of five is a draw after its last move.
    board = [[1 if (x + 2 * y) % 4 < 2 else 2 for x in range(15)] for y in range(15)]
    board[14][14] = 0
    draw_id, _ = service.create_game()
    repo.save(draw_id, GameState(board, 1, GameStatus.IN_PROGRESS))
    draw = service.place_move(draw_id, Move(14, 14))
    assert draw.status == GameStatus.DRAW and draw.winner is None
    assert service.get_game(draw_id) == draw

    # Force a failure after the ORM update: the transaction must roll it back.
    rollback_id, before = service.create_game()
    real_save = GameRepository.save
    def fail_after_save(
        self: GameRepository, game_id: uuid.UUID, state: GameState
    ) -> GameState:
        real_save(self, game_id, state)
        raise RuntimeError("simulated failure")
    with patch.object(GameRepository, "save", fail_after_save):
        try:
            service.place_move(rollback_id, Move(0, 0))
        except RuntimeError:
            pass
        else:
            raise AssertionError("failure did not propagate")
    assert service.get_game(rollback_id) == before

    # Independent DB connections race for the same square. Exactly one wins;
    # the waiter must see the committed stone rather than overwrite it.
    concurrent_id, _ = service.create_game()
    barrier = Barrier(2)
    def make_move() -> GameState | IllegalMoveReason:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                return GameApplicationService().place_move(concurrent_id, Move(8, 8))
            except IllegalMoveError as exc:
                return exc.reason
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: make_move(), range(2)))
    assert sum(isinstance(outcome, GameState) for outcome in outcomes) == 1
    assert outcomes.count(IllegalMoveReason.OCCUPIED) == 1
    final = service.get_game(concurrent_id)
    assert final.board[8][8] == 1 and final.current_player == 2

    # Different positions must also serialize so both turns are retained.
    concurrent_id, _ = service.create_game()
    barrier = Barrier(2)
    def different_move(x: int) -> GameState:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return GameApplicationService().place_move(concurrent_id, Move(x, 0))
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(different_move, (0, 1)))
    final = service.get_game(concurrent_id)
    assert sorted(final.board[0][:2]) == [1, 2] and final.current_player == 1

    cpu_id, initial_cpu = service.create_game(GameMode.CPU)
    assert initial_cpu.mode is GameMode.CPU
    pending = service.place_move(cpu_id, Move(0, 0), expected_revision=0)
    assert pending.board[0][0] == 1 and pending.revision == 1
    assert pending.current_player == 2 and service.get_game(cpu_id) == pending
    try:
        service.place_move(cpu_id, Move(14, 14), expected_revision=1)
    except IllegalMoveError as exc:
        assert exc.reason is IllegalMoveReason.NOT_HUMAN_TURN
    else:
        raise AssertionError("human moved during a pending CPU turn")
    assert service.get_game(cpu_id) == pending

    # Fail after writing the white stone, then verify the black move survived.
    with patch.object(GameRepository, "save", fail_after_save):
        try:
            service.advance_cpu(cpu_id, expected_revision=1)
        except RuntimeError as exc:
            assert str(exc) == "simulated failure"
        else:
            raise AssertionError("CPU save failure did not propagate")
    assert service.get_game(cpu_id) == pending

    # Open both database connections and overlap their attempts at the row lock.
    cpu_barrier = Barrier(2)
    get_for_update = GameRepository.get_for_update
    def overlap_cpu_lock(repository: GameRepository, game_id: uuid.UUID) -> GameState:
        cpu_barrier.wait(timeout=10)
        return get_for_update(repository, game_id)
    def request_cpu(_: int) -> tuple[int, GameState]:
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                backend_pid = cursor.fetchone()[0]
            result = GameApplicationService().advance_cpu(cpu_id, expected_revision=1)
            return backend_pid, result
        finally:
            connection.close()
    with (
        patch.object(GameRepository, "get_for_update", overlap_cpu_lock),
        patch.object(
            game_service, "select_cpu_move", wraps=game_service.select_cpu_move
        ) as selector,
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        results = list(executor.map(request_cpu, range(2)))
        assert selector.call_count == 1
    replied = service.get_game(cpu_id)
    assert results[0][0] != results[1][0]
    assert results[0][1] == results[1][1] == replied
    assert replied.revision == 2 and replied.current_player == 1
    assert replied.mode is GameMode.CPU
    assert replied.board[0][0] == 1 and replied.board[7][7] == 2

    try:
        service.place_move(cpu_id, Move(14, 14), expected_revision=0)
    except IllegalMoveError as exc:
        assert exc.reason is IllegalMoveReason.STALE_REVISION
    else:
        raise AssertionError("a stale human request advanced the game")
    assert service.get_game(cpu_id) == replied
    later_pending = service.place_move(cpu_id, Move(14, 14), expected_revision=2)
    with patch.object(GameRepository, "save", autospec=True) as save:
        assert service.advance_cpu(cpu_id, expected_revision=1) == later_pending
        save.assert_not_called()
    assert service.get_game(cpu_id) == later_pending
    assert later_pending.revision == 3 and later_pending.current_player == 2

    # Terminal CPU moves apply the win-before-draw rule on the final cell.
    for must_win in (False, True):
        last_id, _ = service.create_game(GameMode.CPU)
        last = [[1 if (x + 2 * y) % 4 < 2 else 2 for x in range(15)] for y in range(15)]
        last[14][14] = 0
        if must_win:
            last[14][10:14] = [2, 2, 2, 2]
        near_end = GameState(last, 2, GameStatus.IN_PROGRESS, mode=GameMode.CPU)
        repo.save(last_id, near_end)
        complete = service.advance_cpu(last_id, expected_revision=224)
        assert complete.revision == 225 and complete.mode is GameMode.CPU
        assert complete.board[14][14] == 2 and complete.current_player == 2
        assert complete.status is (GameStatus.WON if must_win else GameStatus.DRAW)
        assert complete.winner == (2 if must_win else None)
        with patch.object(GameRepository, "save", autospec=True) as save:
            assert service.advance_cpu(last_id, expected_revision=225) == complete
            save.assert_not_called()
finally:
    connection.creation.destroy_test_db(old_name, verbosity=0)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
