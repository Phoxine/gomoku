"""Check direct imports against the documented application boundaries."""

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1]
GAME = "app.domain.game"
PERSISTENCE = (f"{GAME}.model", f"{GAME}.models", f"{GAME}.repository")
API_FORBIDDEN = (*PERSISTENCE, "django.db")
RULES_FORBIDDEN = (
    *PERSISTENCE,
    "django",
    "psycopg",
    f"{GAME}.migrations",
    f"{GAME}.service.application_service",
)
RULES_FILES = (
    Path("app/domain/game/service/game_service.py"),
    Path("app/domain/game/state.py"),
)


def imported_names(node: ast.Import | ast.ImportFrom, package: str) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    module = node.module or ""
    if node.level:
        module = resolve_name("." * node.level + module, package)
    return [module, *(f"{module}.{alias.name}" for alias in node.names)]


def boundary_violations(path: Path, source: str) -> list[str]:
    package = ".".join(path.parent.parts)
    if path in RULES_FILES:
        forbidden = RULES_FORBIDDEN
        guidance = (
            "Game rules and state must stay independent of Django and persistence. "
            "Use domain state and keep orchestration in the application service."
        )
    else:
        forbidden = API_FORBIDDEN
        guidance = (
            "API must not import ORM models, repositories, or django.db. "
            "Use GameApplicationService for game operations."
        )
    violations = []
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for name in imported_names(node, package):
            if any(
                name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden
            ):
                violations.append(f"src/{path}:{node.lineno}: {name}. {guidance}")
                break
    return violations


def test_application_import_boundaries() -> None:
    api = SOURCE_ROOT / "app/api"
    paths = sorted(path.relative_to(SOURCE_ROOT) for path in api.rglob("*.py"))
    assert paths, f"No Python sources found in {api}"
    violations = [
        violation
        for path in (*paths, *RULES_FILES)
        for violation in boundary_violations(
            path, (SOURCE_ROOT / path).read_text(encoding="utf-8")
        )
    ]
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize(
    ("path", "source", "expected_import", "entry_point"),
    [
        (
            Path("app/api/views.py"),
            "import app.domain.game.model.game as game",
            f"{GAME}.model.game",
            "Use GameApplicationService",
        ),
        (
            Path("app/api/nested/views.py"),
            "from ...domain.game import repository as repo",
            f"{GAME}.repository",
            "Use GameApplicationService",
        ),
        (
            Path("app/api/views.py"),
            "from app.domain.game import models",
            f"{GAME}.models",
            "Use GameApplicationService",
        ),
        (
            Path("app/api/views.py"),
            "from django import db",
            "django.db",
            "Use GameApplicationService",
        ),
        (
            RULES_FILES[0],
            "from django.db import transaction",
            "django.db",
            "Use domain state",
        ),
        (
            RULES_FILES[0],
            "from . import application_service",
            f"{GAME}.service.application_service",
            "Use domain state",
        ),
        (
            RULES_FILES[1],
            "from .repository import game_repository",
            f"{GAME}.repository",
            "Use domain state",
        ),
    ],
)
def test_import_check_explains_rejected_dependencies(
    path: Path, source: str, expected_import: str, entry_point: str
) -> None:
    (violation,) = boundary_violations(path, f"\n{source}")
    assert violation.startswith(f"src/{path}:2: {expected_import}.")
    assert entry_point in violation


def test_import_check_accepts_supported_dependencies() -> None:
    assert not boundary_violations(
        Path("app/api/views.py"),
        "from django.http import JsonResponse\n"
        "from ..domain.game.service.application_service import GameApplicationService\n"
        "from ..domain.game.state import Move\n",
    )
    assert not boundary_violations(RULES_FILES[0], "from ..state import Move")
    assert not boundary_violations(RULES_FILES[1], "from dataclasses import dataclass")
