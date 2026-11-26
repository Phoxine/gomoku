"""Integration checks for Django game model discovery and migration."""

import subprocess
import sys


def test_game_app_migrates_and_creates_permissions() -> None:
    script = """
import os
import uuid
from unittest.mock import patch
from urllib.parse import urlparse
from django.conf import settings
url = urlparse(os.environ["DATABASE_URL"])
settings.configure(
    SECRET_KEY='test',
    INSTALLED_APPS=[
        'django.contrib.auth', 'django.contrib.contenttypes', 'app.domain.game',
    ],
    DATABASES={'default': {
        'ENGINE': 'django.db.backends.postgresql', 'NAME': url.path[1:],
        'USER': url.username, 'PASSWORD': url.password,
        'HOST': url.hostname, 'PORT': url.port or 5432,
        'TEST': {'NAME': 'gomoku_test_' + uuid.uuid4().hex},
    }},
    USE_TZ=True,
)
import django
django.setup()
from django.apps import apps
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
old_name = connection.settings_dict['NAME']
# Create a disposable database without Django's automatic migration to head.
with patch('django.core.management.call_command'):
    connection.creation.create_test_db(verbosity=0)
try:
    from django.contrib.auth.models import Permission
    from app.domain.game.model.game import Game
    from app.domain.game.model.game_move import GameMove
    from app.domain.game.repository.game_repository import GameRepository
    from app.domain.game.service.application_service import GameApplicationService
    from app.domain.game.state import GameMode, GameStatus, Move

    initial = [('game', '0001_initial')]
    executor = MigrationExecutor(connection)
    executor.migrate(initial)
    OldGame = executor.loader.project_state(initial).apps.get_model('game', 'Game')
    legacy_board = [[0] * 15 for _ in range(15)]
    legacy_board[0][:5] = [1] * 5
    legacy_board[1][:4] = [2] * 4
    legacy = OldGame.objects.create(
        board=legacy_board, current_player=1, status='won', winner=1,
    )

    mode_target = [('game', '0002_game_mode')]
    executor = MigrationExecutor(connection)
    executor.migrate(mode_target)
    ModeGame = executor.loader.project_state(mode_target).apps.get_model('game', 'Game')
    assert ModeGame.objects.get(pk=legacy.pk).mode == 'two_player'
    # A writer from 0001 can still insert and update at 0002.
    overlapping = OldGame.objects.create()
    overlapping.board[14][0] = 1
    overlapping.current_player = 2
    overlapping.save()
    assert ModeGame.objects.get(pk=overlapping.pk).mode == 'two_player'

    active_board = [[0] * 15 for _ in range(15)]
    active_board[0][:6] = [1, 2, 1, 2, 1, 2]
    active_board[14][-6:] = [2, 1, 2, 1, 2, 1]
    active = ModeGame.objects.create(board=active_board, mode='cpu')
    empty = ModeGame.objects.create()
    assert active.current_player == 1 and active.status == 'in_progress'

    call_command('migrate', verbosity=0)
    completed = Game.objects.get(pk=legacy.pk)
    assert completed.mode == 'two_player' and completed.history_start_revision == 9
    assert (
        completed.id, completed.board, completed.current_player, completed.status,
        completed.winner, completed.created_at, completed.updated_at,
    ) == (
        legacy.id, legacy_board, legacy.current_player, legacy.status,
        legacy.winner, legacy.created_at, legacy.updated_at,
    )
    upgraded = Game.objects.get(pk=active.pk)
    assert upgraded.history_start_revision == 12
    assert (
        upgraded.id, upgraded.mode, upgraded.board, upgraded.current_player,
        upgraded.status, upgraded.winner, upgraded.created_at, upgraded.updated_at,
    ) == (
        active.id, active.mode, active_board, active.current_player,
        active.status, active.winner, active.created_at, active.updated_at,
    )
    old_writer_state = GameRepository().get(overlapping.pk)
    assert old_writer_state.mode is GameMode.TWO_PLAYER
    assert old_writer_state.status is GameStatus.IN_PROGRESS
    assert old_writer_state.current_player == 2 and old_writer_state.revision == 1
    assert old_writer_state.board[14][0] == 1
    assert Game.objects.get(pk=overlapping.pk).history_start_revision == 1
    assert Game.objects.get(pk=empty.pk).history_start_revision == 0
    assert not GameMove.objects.exists()

    service = GameApplicationService()
    service.place_move(active.pk, Move(0, 1), expected_revision=12)
    service.advance_cpu(active.pk, expected_revision=13)
    resumed = service.place_move(active.pk, Move(0, 2), expected_revision=14)
    history = GameRepository().read_verified_history(active.pk)
    assert history.state == resumed and history.start_revision == 12
    assert [(row.move_number, row.player) for row in history.moves] == [
        (13, 1), (14, 2), (15, 1),
    ]

    assert apps.get_app_config('game').models_module is not None
    call_command('makemigrations', 'game', check=True, dry_run=True, verbosity=0)
    transaction.set_autocommit(False)
    a = Game.objects.create()
    b = Game.objects.create()
    cpu = Game.objects.create(mode='cpu')
    assert a.mode == 'two_player' and cpu.mode == 'cpu'
    assert a.history_start_revision == 0
    assert Game.objects.get(pk=cpu.pk).mode == 'cpu'
    first_move_fields = dict(game_id=a.pk, move_number=1, player=1, x=0, y=14)
    first_move = GameMove.objects.create(**first_move_fields)
    GameMove.objects.create(game_id=a.pk, move_number=225, player=2, x=14, y=0)
    GameMove.objects.create(**(first_move_fields | {'game_id': b.pk}))
    move_numbers = a.moves.order_by('move_number').values_list('move_number', flat=True)
    assert list(move_numbers) == [1, 225]

    def assert_history_write_rejected(write, scenario):
        try:
            with transaction.atomic():
                write()
                # The game foreign key is initially deferred in PostgreSQL.
                connection.check_constraints()
        except IntegrityError:
            return
        raise AssertionError(f'database accepted invalid history write: {scenario}')

    for invalid_fields in [
        {'x': 1},  # Existing move number at a different position.
        {'move_number': 2},  # Existing position with a different move number.
        {'move_number': 0, 'x': 1},
        {'move_number': 226, 'x': 1},
        {'move_number': 2, 'player': 0, 'x': 1},
        {'move_number': 2, 'player': 3, 'x': 1},
        {'move_number': 2, 'x': -1},
        {'move_number': 2, 'x': 15},
        {'move_number': 2, 'y': -1},
        {'move_number': 2, 'y': 15},
        {'game_id': uuid.uuid4()},
    ]:
        assert_history_write_rejected(
            lambda: GameMove.objects.create(**(first_move_fields | invalid_fields)),
            invalid_fields,
        )
    for invalid_boundary in (-1, 226, None):
        assert_history_write_rejected(
            lambda: Game.objects.create(history_start_revision=invalid_boundary),
            invalid_boundary,
        )
    try:
        with transaction.atomic():
            Game.objects.create(mode='spectator')
    except IntegrityError:
        pass
    else:
        raise AssertionError('unsupported mode accepted by the database')
    assert str(a) == f'Game {a.pk} ({a.status})'
    assert len(a.board) == 15 and all(len(row) == 15 for row in a.board)
    a.board[0][0] = 1
    assert b.board[0][0] == 0
    for status, winner, allowed in [
        ("won", 1, True), ("won", 2, True), ("won", None, False),
        ("in_progress", 1, False), ("draw", 2, False),
    ]:
        try:
            with transaction.atomic():
                Game.objects.create(status=status, winner=winner)
        except IntegrityError:
            assert not allowed
        else:
            assert allowed
    from copy import deepcopy
    valid = [[0 for _ in range(15)] for _ in range(15)]
    invalid_boards = [None, {}, [], [0] * 15, valid[:14]]
    for invalid_value in (3, -1, True, None, "1", [], {}, 0.0, 1.0, 2.0):
        board = deepcopy(valid)
        board[0][0] = invalid_value
        invalid_boards.append(board)
    short_row = deepcopy(valid)
    short_row[0] = short_row[0][:-1]
    invalid_boards.append(short_row)
    from django.db import DatabaseError
    for board in invalid_boards:
        for write in (
            lambda: Game.objects.create(board=board),
            lambda: Game.objects.filter(pk=a.pk).update(board=board),
            lambda: Game.objects.bulk_create([Game(board=board)]),
        ):
            try:
                with transaction.atomic():
                    write()
            except DatabaseError:
                pass
            else:
                raise AssertionError(f"invalid board accepted: {board!r}")
    a.delete()
    assert not GameMove.objects.filter(pk=first_move.pk).exists()
    assert b.moves.count() == 1
    assert Permission.objects.filter(
        content_type__app_label='game', codename='add_game',
    ).exists()
finally:
    if not connection.get_autocommit():
        transaction.rollback()
        transaction.set_autocommit(True)
    connection.creation.destroy_test_db(old_name, verbosity=0)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
