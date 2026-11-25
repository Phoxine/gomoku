"""HTTP adapters for game operations."""

import json
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from app.api.game_dto import (
    CpuMoveRequest,
    CreateGameRequest,
    CsrfResponse,
    ErrorResponse,
    GameResponse,
    MoveRequest,
)
from app.domain.game.service.application_service import (
    GameApplicationService,
    GameNotFoundError,
)
from app.domain.game.service.game_service import BOARD_SIZE
from app.domain.game.state import GameMode, IllegalMoveError, IllegalMoveReason


def json_object(request: HttpRequest) -> dict[str, object] | None:
    try:
        data = json.loads(request.body)
    except ValueError, RecursionError:
        return None
    return data if isinstance(data, dict) else None


def error_response(code: str, status: int = 400) -> JsonResponse:
    return JsonResponse(ErrorResponse(code).to_dict(), status=status)


def valid_revision(value: object) -> bool:
    return type(value) is int and 0 <= value <= BOARD_SIZE**2


def move_field_error(game_id: UUID, code: str, *, has_revision: bool) -> JsonResponse:
    if has_revision:
        # Preserve the coordinate-only contract's extra-field error. Mode is
        # immutable, so rejected requests need only a read, not a row lock.
        try:
            state = GameApplicationService().get_game(game_id)
        except GameNotFoundError:
            return error_response("invalid_request")
        if state.mode is not GameMode.CPU:
            return error_response("invalid_request")
    return error_response(code)


@require_GET
@ensure_csrf_cookie
def csrf_cookie(request: HttpRequest) -> JsonResponse:
    return JsonResponse(CsrfResponse().to_dict())


@require_POST
def create_game(request: HttpRequest) -> JsonResponse:
    create = CreateGameRequest()
    if request.content_type == "application/json" and request.body:
        data = json_object(request)
        if data is None or data.keys() - {"mode"}:
            return error_response("invalid_request")
        if "mode" in data:
            try:
                create = CreateGameRequest(GameMode(data["mode"]))
            except ValueError:
                return error_response("invalid_mode")
    if create.mode is GameMode.CPU and not settings.CPU_CREATION_ENABLED:
        return error_response("cpu_creation_unavailable", 503)
    game_id, state = GameApplicationService().create_game(create.mode)
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict(), status=201)


@require_GET
def get_game(request: HttpRequest, game_id: UUID) -> JsonResponse:
    try:
        state = GameApplicationService().get_game(game_id)
    except GameNotFoundError:
        return error_response("game_not_found", 404)
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict())


@require_POST
def place_move(request: HttpRequest, game_id: UUID) -> JsonResponse:
    if request.content_type != "application/json":
        return error_response("unsupported_media_type", 415)
    data = json_object(request)
    if data is None or data.keys() not in ({"x", "y"}, {"x", "y", "expected_revision"}):
        return error_response("invalid_request")
    has_revision = "expected_revision" in data
    if type(data["x"]) is not int or type(data["y"]) is not int:
        return move_field_error(
            game_id, "invalid_coordinate", has_revision=has_revision
        )
    revision = data.get("expected_revision")
    if has_revision and not valid_revision(revision):
        return move_field_error(game_id, "invalid_revision", has_revision=True)
    move = MoveRequest(x=data["x"], y=data["y"], expected_revision=revision)
    try:
        state = GameApplicationService().place_move(
            game_id, move.to_domain(), move.expected_revision
        )
    except GameNotFoundError:
        return error_response("game_not_found", 404)
    except IllegalMoveError as exc:
        status = (
            409
            if exc.reason
            in (
                IllegalMoveReason.OCCUPIED,
                IllegalMoveReason.GAME_FINISHED,
                IllegalMoveReason.NOT_HUMAN_TURN,
                IllegalMoveReason.STALE_REVISION,
            )
            else 400
        )
        return error_response(exc.reason.value, status)
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict())


@require_POST
def advance_cpu(request: HttpRequest, game_id: UUID) -> JsonResponse:
    if request.content_type != "application/json":
        return error_response("unsupported_media_type", 415)
    data = json_object(request)
    if data is None or data.keys() != {"expected_revision"}:
        return error_response("invalid_request")
    revision = data["expected_revision"]
    if not valid_revision(revision):
        return error_response("invalid_revision")
    move = CpuMoveRequest(expected_revision=revision)
    try:
        state = GameApplicationService().advance_cpu(game_id, move.expected_revision)
    except GameNotFoundError:
        return error_response("game_not_found", 404)
    except IllegalMoveError as exc:
        return error_response(exc.reason.value, 409)
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict())
