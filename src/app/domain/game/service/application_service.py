"""Coordinate game rules and transactional persistence."""

from uuid import UUID

from django.db import transaction

from app.domain.game.repository.game_repository import GameRepository
from app.domain.game.service import game_service
from app.domain.game.state import (
    GameState,
    GameStatus,
    Move,
)


class GameApplicationService:
    def __init__(self, repository: GameRepository | None = None) -> None:
        self.repository = repository if repository is not None else GameRepository()

    def create_game(self) -> tuple[UUID, GameState]:
        return self.repository.create(
            GameState(game_service.initialize_board(), 1, GameStatus.IN_PROGRESS)
        )

    def get_game(self, game_id: UUID) -> GameState:
        return self.repository.get(game_id)

    def place_move(self, game_id: UUID, move: Move) -> GameState:
        with transaction.atomic():
            state = self.repository.get_for_update(game_id)
            return self.repository.save(
                game_id, game_service.apply_move(state, move)
            )
