"""Expose domain models for Django app discovery."""

from app.domain.game.model.game import Game
from app.domain.game.model.game_move import GameMove

__all__ = ["Game", "GameMove"]
