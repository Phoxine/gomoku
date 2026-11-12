"""Check the web page and its static assets in an isolated Django process."""

import os
import subprocess
import sys
from pathlib import Path


def test_game_page_and_static_assets() -> None:
    script = """
import os
from wsgiref.util import setup_testing_defaults

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import django
django.setup()
from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.handlers.wsgi import WSGIHandler
from django.test import Client

settings.ALLOWED_HOSTS = ["testserver"]
response = Client().get("/")
assert response.status_code == 200
assert response.headers["Content-Type"].startswith("text/html")
html = response.content.decode()
assert 'id="board"' in html or "id='board'" in html
for path in ("/static/game/game.js", "/static/game/game.css"):
    assert path in html
    environ = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = path
    environ["HTTP_HOST"] = "testserver"
    status = []
    handler = StaticFilesHandler(WSGIHandler())
    result = handler(environ, lambda code, headers, exc_info=None: status.append(code))
    try:
        content = b"".join(result)
    finally:
        if hasattr(result, "close"):
            result.close()
    assert status[0].startswith("200 "), (path, status)
    assert content, path
"""
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SECRET_KEY": "test-key",
            "DEBUG": "True",
            "DATABASE_URL": "postgresql://user:password@db:5432/game",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
