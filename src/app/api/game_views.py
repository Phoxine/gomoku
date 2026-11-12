"""HTTP adapters for game operations."""

import json
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from app.api.game_dto import GameResponse, MoveRequest
from app.domain.game.service.application_service import (
    GameApplicationService,
    GameNotFoundError,
)
from app.domain.game.state import IllegalMoveError, IllegalMoveReason


@require_GET
@ensure_csrf_cookie
def csrf_cookie(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"detail": "CSRF cookie set"})


@require_POST
def create_game(request: HttpRequest) -> JsonResponse:
    game_id, state = GameApplicationService().create_game()
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict(), status=201)


@require_GET
def get_game(request: HttpRequest, game_id: UUID) -> JsonResponse:
    try:
        state = GameApplicationService().get_game(game_id)
    except GameNotFoundError:
        return JsonResponse({"error": "game_not_found"}, status=404)
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict())


@require_POST
def place_move(request: HttpRequest, game_id: UUID) -> HttpResponse:
    if request.content_type != "application/json":
        return JsonResponse({"error": "unsupported_media_type"}, status=415)
    try:
        data = json.loads(request.body)
    except ValueError, UnicodeDecodeError, RecursionError:
        return JsonResponse({"error": "invalid_request"}, status=400)
    if not isinstance(data, dict) or set(data) != {"x", "y"}:
        return JsonResponse({"error": "invalid_request"}, status=400)
    if type(data["x"]) is not int or type(data["y"]) is not int:
        return JsonResponse({"error": "invalid_coordinate"}, status=400)
    move = MoveRequest(x=data["x"], y=data["y"])
    try:
        state = GameApplicationService().place_move(game_id, move.to_domain())
    except GameNotFoundError:
        return JsonResponse({"error": "game_not_found"}, status=404)
    except IllegalMoveError as exc:
        status = (
            409
            if exc.reason
            in (IllegalMoveReason.OCCUPIED, IllegalMoveReason.GAME_FINISHED)
            else 400
        )
        return JsonResponse({"error": exc.reason.value}, status=status)
    return JsonResponse(GameResponse.from_state(game_id, state).to_dict())
