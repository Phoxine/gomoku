"""Exercise HTTP game operations with CSRF and PostgreSQL persistence."""

import subprocess
import sys


def test_move_request_boundary_without_database() -> None:
    script = """
import json
import os
from unittest.mock import patch
from uuid import uuid4

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from django.test import RequestFactory

from app.api import game_views
from app.api.game_dto import MoveRequest
from app.domain.game.service.game_service import initialize_board
from app.domain.game.state import GameState, GameStatus, Move

factory = RequestFactory()
game_id = uuid4()
state = GameState(initialize_board(), 1, GameStatus.IN_PROGRESS)

with patch.object(game_views, 'GameApplicationService') as service:
    for body, error in [
        (b'{"x": 0, "y":', 'invalid_request'),
        (b'{"x": 0, "y": "\\xff"}', 'invalid_request'),
        ('null', 'invalid_request'),
        ('{"y": 0}', 'invalid_request'),
        ('{"x": 0, "y": 0, "z": 0}', 'invalid_request'),
        ('{"x": true, "y": 0}', 'invalid_coordinate'),
        ('{"x": 0, "y": false}', 'invalid_coordinate'),
        ('{"x": 0, "y": 1.0}', 'invalid_coordinate'),
        ('{"x": 0, "y": "1"}', 'invalid_coordinate'),
        ('{"x": 0, "y": null}', 'invalid_coordinate'),
    ]:
        request = factory.post('/', body, content_type='application/json')
        response = game_views.place_move(request, game_id)
        assert response.status_code == 400
        assert json.loads(response.content) == {'error': error}
        service.assert_not_called()

    request = factory.post('/', 'x=0&y=0', content_type='text/plain')
    response = game_views.place_move(request, game_id)
    assert response.status_code == 415
    service.assert_not_called()

    service.return_value.place_move.return_value = state
    with patch.object(
        game_views, 'MoveRequest', side_effect=MoveRequest
    ) as request_dto:
        for x, y in [(3, 4), (-1, 15)]:
            body = json.dumps({'x': x, 'y': y})
            request = factory.post('/', body, content_type='application/json')
            response = game_views.place_move(request, game_id)
            assert response.status_code == 200
            request_dto.assert_called_once_with(x=x, y=y, expected_revision=None)
            service.assert_called_once_with()
            service.return_value.place_move.assert_called_once_with(
                game_id, Move(x, y), None
            )
            request_dto.reset_mock()
            service.reset_mock()
"""
    subprocess.run([sys.executable, "-c", script], check=True)


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
from django.test import Client, override_settings

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
    assert set(state) == {
        'id', 'board', 'current_player', 'status', 'winner', 'mode', 'revision',
    }
    assert state['board'] == [[0] * 15 for _ in range(15)]
    assert state['current_player'] == 1
    assert state['status'] == 'in_progress' and state['winner'] is None
    assert state['mode'] == 'two_player' and state['revision'] == 0
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
    assert moved_state['mode'] == 'two_player' and moved_state['revision'] == 1
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

    def post_json(url: str, body: object) -> HttpResponse:
        return client.post(
            url, data=json.dumps(body), content_type='application/json', **headers,
        )

    def assert_error(response: HttpResponse, status: int, code: str) -> None:
        assert response.status_code == status
        assert response.json() == {'error': code}

    legacy_form = client.post(games, data={'csrfmiddlewaretoken': token, 'mode': 'cpu'})
    assert legacy_form.status_code == 201
    assert legacy_form.json()['mode'] == 'two_player'
    for body in ({}, {'mode': 'two_player'}):
        created = post_json(games, body)
        assert created.status_code == 201
        assert created.json()['mode'] == 'two_player'
    assert_error(
        client.post(games, data='{', content_type='application/json', **headers),
        400, 'invalid_request',
    )
    for body in ([], None, {'mode': 'cpu', 'extra': 1}):
        assert_error(post_json(games, body), 400, 'invalid_request')
    for mode in ('random', True, 1, None, [], {}):
        assert_error(post_json(games, {'mode': mode}), 400, 'invalid_mode')

    with override_settings(CPU_CREATION_ENABLED=False):
        assert_error(post_json(games, {'mode': 'cpu'}), 503, 'cpu_creation_unavailable')
        created_two_player = client.post(games, **headers)
        assert created_two_player.status_code == 201
        assert created_two_player.json()['mode'] == 'two_player'

    created = post_json(games, {'mode': 'cpu'})
    assert created.status_code == 201
    cpu_start = created.json()
    assert cpu_start['mode'] == 'cpu' and cpu_start['revision'] == 0
    assert cpu_start['current_player'] == 1 and cpu_start['status'] == 'in_progress'
    assert cpu_start['winner'] is None and cpu_start['board'] == state['board']
    cpu_game_url = f"{games}{cpu_start['id']}/"
    cpu_move_url = cpu_game_url + 'cpu-move/'
    human_move_url = cpu_game_url + 'moves/'
    assert client.get(cpu_move_url).status_code == 405
    missing_csrf = client.post(cpu_move_url, {}, content_type='application/json')
    assert missing_csrf.status_code == 403
    assert_error(
        post_json(game_url + 'cpu-move/', {'expected_revision': 0}),
        409, 'not_cpu_game',
    )
    assert_error(
        post_json(move_url, {'x': 9, 'y': 9, 'expected_revision': 0}),
        400, 'invalid_request',
    )
    assert_error(
        post_json(move_url, {'x': 9, 'y': 9, 'expected_revision': None}),
        400, 'invalid_request',
    )
    assert_error(
        post_json(move_url, {'x': False, 'y': 9, 'expected_revision': 0}),
        400, 'invalid_request',
    )
    assert_error(
        post_json(missing + 'cpu-move/', {'expected_revision': 0}),
        404, 'game_not_found',
    )
    assert_error(
        client.post(
            cpu_move_url, data='revision=0', content_type='text/plain', **headers
        ),
        415, 'unsupported_media_type',
    )
    for body in ('{', '[]', '{}', '{"expected_revision": 1, "extra": 0}'):
        response = client.post(
            cpu_move_url, data=body, content_type='application/json', **headers,
        )
        assert_error(response, 400, 'invalid_request')
    assert_error(post_json(human_move_url, {'x': 0, 'y': 0}), 400, 'invalid_request')
    for revision in (-1, 226, True, 1.0, '1', None):
        assert_error(
            post_json(cpu_move_url, {'expected_revision': revision}),
            400, 'invalid_revision',
        )
        assert_error(
            post_json(human_move_url, {'x': 0, 'y': 0, 'expected_revision': revision}),
            400, 'invalid_revision',
        )
    for revision in (0, 225):
        no_move = post_json(cpu_move_url, {'expected_revision': revision})
        assert no_move.status_code == 200 and no_move.json() == cpu_start

    pending_response = post_json(
        human_move_url, {'x': 0, 'y': 14, 'expected_revision': 0}
    )
    assert pending_response.status_code == 200
    pending = pending_response.json()
    assert pending['id'] == cpu_start['id'] and pending['mode'] == 'cpu'
    assert pending['revision'] == 1 and pending['current_player'] == 2
    assert pending['board'][14][0] == 1
    assert client.get(cpu_game_url).json() == pending
    assert_error(
        post_json(human_move_url, {'x': 14, 'y': 0, 'expected_revision': 1}),
        409, 'not_human_turn',
    )
    reply = post_json(cpu_move_url, {'expected_revision': 1})
    assert reply.status_code == 200
    replied = reply.json()
    assert replied['id'] == cpu_start['id'] and replied['mode'] == 'cpu'
    assert replied['revision'] == 2 and replied['current_player'] == 1
    assert replied['board'][14][0] == 1 and replied['board'][7][7] == 2
    assert client.get(cpu_game_url).json() == replied
    assert_error(
        post_json(human_move_url, {'x': 14, 'y': 0, 'expected_revision': 0}),
        409, 'stale_revision',
    )
    replay = post_json(cpu_move_url, {'expected_revision': 1})
    assert replay.status_code == 200 and replay.json() == replied
finally:
    connection.creation.destroy_test_db(old_name, verbosity=0)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
