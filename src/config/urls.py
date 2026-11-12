"""Project URL routes."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from django.urls import path
from django.views.generic import TemplateView

from app.api import game_views

urlpatterns = [
    path("", TemplateView.as_view(template_name="game.html"), name="game-page"),
    path("api/v1/csrf/", game_views.csrf_cookie, name="csrf-cookie"),
    path("api/v1/games/", game_views.create_game, name="game-create"),
    path("api/v1/games/<uuid:game_id>/", game_views.get_game, name="game-detail"),
    path("api/v1/games/<uuid:game_id>/moves/", game_views.place_move, name="game-move"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, view=serve)
