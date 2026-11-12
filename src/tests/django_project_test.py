"""Exercise the Django project configuration in isolated processes."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1]


def run_python(
    *args: str, overrides: dict[str, str | None] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SECRET_KEY": "test-key",
            "DEBUG": "False",
            "DATABASE_URL": "postgresql://user%40example:pass%40word@db:5432/game%20db",
        }
    )
    for key, value in (overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(
        [sys.executable, *args],
        cwd=SRC_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_manage_check_and_server_entry_points() -> None:
    result = run_python("manage.py", "check")
    assert result.returncode == 0, result.stderr

    result = run_python(
        "-c",
        "from config.wsgi import application as wsgi; "
        "from config.asgi import application as asgi; "
        "assert callable(wsgi) and callable(asgi)",
    )
    assert result.returncode == 0, result.stderr


def test_database_url_decodes_components_and_debug() -> None:
    result = run_python(
        "-c",
        "from config import settings; "
        "db = settings.DATABASES['default']; "
        "assert db['ENGINE'] == 'django.db.backends.postgresql'; "
        "assert db['USER'] == 'user@example'; "
        "assert db['PASSWORD'] == 'pass@word'; "
        "assert db['NAME'] == 'game db'; "
        "assert db['HOST'] == 'db'; "
        "assert str(db['PORT']) == '5432'; "
        "assert settings.DEBUG is True",
        overrides={"DEBUG": "True"},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "overrides",
    [
        {"DJANGO_SECRET_KEY": None},
        {"DJANGO_SECRET_KEY": ""},
        {"DATABASE_URL": None},
        {"DATABASE_URL": ""},
        {"DATABASE_URL": "sqlite:///game.db"},
        {"DATABASE_URL": "postgresql://user:password@db:0/game"},
        {"DEBUG": "perhaps"},
    ],
)
def test_invalid_configuration_fails_at_startup(
    overrides: dict[str, str | None],
) -> None:
    result = run_python("manage.py", "check", overrides=overrides)
    assert result.returncode != 0
