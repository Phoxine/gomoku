"""Django persistence for game states."""

from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from app.domain.game.model.game import Game
from app.domain.game.model.game_move import GameMove
from app.domain.game.state import (
    ForbiddenMovePolicy,
    GameMode,
    GameResultReason,
    GameState,
    GameStatus,
    Move,
    Player,
)


class GameNotFoundError(LookupError):
    """The requested game does not exist."""


class InconsistentGameHistoryError(ValueError):
    """Recorded moves do not match the saved game."""


@dataclass(frozen=True, slots=True)
class RecordedMove:
    move_number: int
    move: Move
    player: Player


@dataclass(frozen=True, slots=True)
class GameHistory:
    state: GameState
    start_revision: int
    moves: tuple[RecordedMove, ...]


class GameRepository:
    """Translate between persisted games and framework-independent state."""

    @staticmethod
    def _state(game: Game) -> GameState:
        return GameState(
            board=[row.copy() for row in game.board],
            current_player=game.current_player,
            status=GameStatus(game.status),
            winner=game.winner,
            mode=GameMode(game.mode),
            forbidden_move_policy=ForbiddenMovePolicy(game.forbidden_move_policy),
            result_reason=(
                GameResultReason(game.result_reason)
                if game.result_reason is not None
                else None
            ),
        )

    def create(self, state: GameState) -> tuple[UUID, GameState]:
        game = Game.objects.create(
            board=state.board,
            current_player=state.current_player,
            status=state.status.value,
            winner=state.winner,
            mode=state.mode.value,
            forbidden_move_policy=state.forbidden_move_policy,
            result_reason=state.result_reason,
            history_start_revision=state.revision,
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
        game.result_reason = state.result_reason
        game.save(
            update_fields=[
                "board",
                "current_player",
                "status",
                "winner",
                "result_reason",
                "updated_at",
            ]
        )
        return self._state(game)

    def save_move(
        self, game_id: UUID, state: GameState, move: Move, player: Player
    ) -> GameState:
        """Persist an accepted move inside the caller's locked transaction."""
        saved = self.save(game_id, state)
        GameMove.objects.create(
            game_id=game_id,
            move_number=saved.revision,
            player=player,
            x=move.x,
            y=move.y,
        )
        return saved

    def read_verified_history(self, game_id: UUID) -> GameHistory:
        with transaction.atomic():
            game = self._get(game_id, lock=True)
            state = self._state(game)
            start_revision = game.history_start_revision
            revision = state.revision
            rows = GameMove.objects.filter(game_id=game_id).order_by("move_number")
            moves = tuple(
                RecordedMove(row.move_number, Move(row.x, row.y), row.player)
                for row in rows
            )
            if not 0 <= start_revision <= revision or tuple(
                move.move_number for move in moves
            ) != tuple(range(start_revision + 1, revision + 1)):
                raise InconsistentGameHistoryError(
                    f"Game {game_id} has an inconsistent move range"
                )
            for recorded in moves:
                if state.board[recorded.move.y][recorded.move.x] != recorded.player:
                    raise InconsistentGameHistoryError(
                        f"Game {game_id} move {recorded.move_number} "
                        "disagrees with the board"
                    )
            return GameHistory(state, start_revision, moves)
