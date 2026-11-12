"""Django persistence for game states."""

from uuid import UUID

from app.domain.game.model.game import Game
from app.domain.game.state import GameState, GameStatus


class GameNotFoundError(LookupError):
    """The requested game does not exist."""


class GameRepository:
    """Translate between persisted games and framework-independent state."""

    @staticmethod
    def _state(game: Game) -> GameState:
        return GameState(
            board=[row.copy() for row in game.board],
            current_player=game.current_player,
            status=GameStatus(game.status),
            winner=game.winner,
        )

    def create(self, state: GameState) -> tuple[UUID, GameState]:
        game = Game.objects.create(
            board=state.board,
            current_player=state.current_player,
            status=state.status.value,
            winner=state.winner,
        )
        return game.pk, self._state(game)

    def _get(self, game_id: UUID, *, lock: bool) -> Game:
        games = Game.objects.select_for_update() if lock else Game.objects.all()
        try:
            return games.get(pk=game_id)
        except Game.DoesNotExist as exc:
            raise GameNotFoundError(f"Game {game_id} does not exist") from exc

    def get(self, game_id: UUID) -> GameState:
        return self._state(self._get(game_id, lock=False))

    def get_for_update(self, game_id: UUID) -> GameState:
        """Read and lock a game; the caller must hold a transaction."""
        return self._state(self._get(game_id, lock=True))

    def save(self, game_id: UUID, state: GameState) -> GameState:
        game = self._get(game_id, lock=False)
        game.board = state.board
        game.current_player = state.current_player
        game.status = state.status.value
        game.winner = state.winner
        game.save(
            update_fields=["board", "current_player", "status", "winner", "updated_at"]
        )
        return self._state(game)
