"""Exercise HTTP game operations with CSRF and PostgreSQL persistence."""

import subprocess
import sys


def test_game_api_with_postgres() -> None:
    # Use a separate process so Django settings do not affect domain unit tests.
    script = """
import json
import os
import uuid

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.test import Client

settings.ALLOWED_HOSTS = ['testserver']
connection.settings_dict['TEST']['NAME'] = 'gomoku_test_' + uuid.uuid4().hex
old_name = connection.settings_dict['NAME']
connection.creation.create_test_db(verbosity=0)
try:
    client = Client(enforce_csrf_checks=True)
    games = '/api/v1/games/'

    assert client.post(games).status_code == 403
    csrf_response = client.get('/api/v1/csrf/')
    assert csrf_response.status_code == 200
    token = csrf_response.cookies['csrftoken'].value
    headers = {'HTTP_X_CSRFTOKEN': token}
    response = client.post(games, **headers)
    assert response.status_code == 201
    state = response.json()
    game_id = uuid.UUID(state['id'])
    assert set(state) == {'id', 'board', 'current_player', 'status', 'winner'}
    assert state['board'] == [[0] * 15 for _ in range(15)]
    assert state['current_player'] == 1
    assert state['status'] == 'in_progress' and state['winner'] is None
    game_url = f'{games}{game_id}/'
    move_url = f'{game_url}moves/'
    assert client.get(game_url).json() == state
    assert client.get(move_url).status_code == 405
    assert client.put(game_url, **headers).status_code == 405

    def post_move(
        body: str, content_type: str = 'application/json'
    ) -> HttpResponse:
        return client.post(move_url, data=body, content_type=content_type, **headers)

    for body in ('{', '[]', '{}', '{"x": 0}', '{"x": 0, "y": 0, "z": 1}'):
        invalid = post_move(body)
        assert invalid.status_code == 400
        assert invalid.json() == {'error': 'invalid_request'}
    nested = post_move("[" * 2000 + "0" + "]" * 2000)
    assert nested.status_code == 400 and nested.json() == {"error": "invalid_request"}
    for x in (True, 1.5, "1", None):
        invalid = post_move(json.dumps({"x": x, "y": 0}))
        assert invalid.status_code == 400
        assert invalid.json() == {"error": "invalid_coordinate"}
    unsupported = post_move('x=0&y=0', 'application/x-www-form-urlencoded')
    assert unsupported.status_code == 415
    assert unsupported.json() == {'error': 'unsupported_media_type'}

    out_of_bounds = post_move(json.dumps({'x': -1, 'y': 0}))
    assert out_of_bounds.status_code == 400
    assert out_of_bounds.json() == {'error': 'out_of_bounds'}
    moved = post_move(json.dumps({'x': 3, 'y': 4}))
    assert moved.status_code == 200
    moved_state = moved.json()
    assert moved_state['id'] == str(game_id)
    assert moved_state['board'][4][3] == 1 and moved_state['current_player'] == 2
    assert client.get(game_url).json() == moved_state
    occupied = post_move(json.dumps({'x': 3, 'y': 4}))
    assert occupied.status_code == 409
    assert occupied.json() == {'error': 'occupied'}
    assert client.get(game_url).json() == moved_state

    missing = f'{games}{uuid.uuid4()}/'
    missing_response = client.get(missing)
    assert missing_response.status_code == 404
    assert missing_response.json() == {'error': 'game_not_found'}
    missing_move = client.post(
        missing + 'moves/', data='{"x": 0, "y": 0}',
        content_type='application/json', **headers,
    )
    assert missing_move.status_code == 404
    assert missing_move.json() == {'error': 'game_not_found'}

    # Player 2 and player 1 alternate; player 1 completes a horizontal line.
    for x, y in [
        (0, 1), (0, 0), (2, 1), (1, 0), (4, 1),
        (2, 0), (6, 1), (3, 0), (8, 1),
    ]:
        assert post_move(json.dumps({'x': x, 'y': y})).status_code == 200
    win = post_move(json.dumps({'x': 4, 'y': 0}))
    assert win.status_code == 200
    assert win.json()['status'] == 'won' and win.json()['winner'] == 1
    finished = post_move(json.dumps({'x': 5, 'y': 0}))
    assert finished.status_code == 409
    assert finished.json() == {'error': 'game_finished'}
finally:
    connection.creation.destroy_test_db(old_name, verbosity=0)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
