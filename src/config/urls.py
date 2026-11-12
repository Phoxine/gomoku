"""Project URL routes."""

from django.urls import path

from app.api import game_views

urlpatterns = [
    path("api/v1/csrf/", game_views.csrf_cookie, name="csrf-cookie"),
    path("api/v1/games/", game_views.create_game, name="game-create"),
    path("api/v1/games/<uuid:game_id>/", game_views.get_game, name="game-detail"),
    path("api/v1/games/<uuid:game_id>/moves/", game_views.place_move, name="game-move"),
]
