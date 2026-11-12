"""Integration checks for Django game model discovery and migration."""

import subprocess
import sys


def test_game_app_migrates_and_creates_permissions() -> None:
    script = """
import os
import uuid
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
from django.db import connection, transaction
old_name = connection.settings_dict['NAME']
connection.creation.create_test_db(verbosity=0)
try:
    from django.contrib.auth.models import Permission
    from app.domain.game.model.game import Game
    assert apps.get_app_config('game').models_module is not None
    call_command('makemigrations', 'game', check=True, dry_run=True, verbosity=0)
    call_command('migrate', verbosity=0)
    transaction.set_autocommit(False)
    a = Game.objects.create()
    b = Game.objects.create()
    assert len(a.board) == 15 and all(len(row) == 15 for row in a.board)
    a.board[0][0] = 1
    assert b.board[0][0] == 0
    from django.db import IntegrityError
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
