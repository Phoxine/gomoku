"""Coordinate game rules and transactional persistence."""

from uuid import UUID

from django.db import transaction

from app.domain.game.repository.game_repository import GameNotFoundError, GameRepository
from app.domain.game.service import game_service
from app.domain.game.state import (
    GameMode,
    GameState,
    GameStatus,
    IllegalMoveError,
    IllegalMoveReason,
    Move,
)

__all__ = ["GameApplicationService", "GameNotFoundError"]


class GameApplicationService:
    def __init__(self, repository: GameRepository | None = None) -> None:
        self.repository = repository if repository is not None else GameRepository()

    def create_game(
        self, mode: GameMode = GameMode.TWO_PLAYER
    ) -> tuple[UUID, GameState]:
        return self.repository.create(
            GameState(
                game_service.initialize_board(), 1, GameStatus.IN_PROGRESS, mode=mode
            )
        )

    def get_game(self, game_id: UUID) -> GameState:
        return self.repository.get(game_id)

    def place_move(
        self, game_id: UUID, move: Move, expected_revision: int | None = None
    ) -> GameState:
        with transaction.atomic():
            state = self.repository.get_for_update(game_id)
            if (state.mode is GameMode.CPU) != (expected_revision is not None):
                raise IllegalMoveError(IllegalMoveReason.INVALID_REQUEST)
            if state.mode is GameMode.CPU and state.status is GameStatus.IN_PROGRESS:
                if state.current_player != 1:
                    raise IllegalMoveError(IllegalMoveReason.NOT_HUMAN_TURN)
                if expected_revision != state.revision:
                    raise IllegalMoveError(IllegalMoveReason.STALE_REVISION)
            return self.repository.save(game_id, game_service.apply_move(state, move))

    def advance_cpu(self, game_id: UUID, expected_revision: int) -> GameState:
        with transaction.atomic():
            state = self.repository.get_for_update(game_id)
            if state.mode is not GameMode.CPU:
                raise IllegalMoveError(IllegalMoveReason.NOT_CPU_GAME)
            if (
                state.status is not GameStatus.IN_PROGRESS
                or state.current_player != 2
                or expected_revision != state.revision
            ):
                return state

            move = game_service.select_cpu_move(state.board)
            if move is None:
                raise ValueError("Pending CPU turn has no legal move")
            return self.repository.save(game_id, game_service.apply_move(state, move))
