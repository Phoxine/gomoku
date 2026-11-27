"""Request and response data for game endpoints."""

from dataclasses import asdict, dataclass
from uuid import UUID

from app.domain.game.state import (
    Board,
    ForbiddenMovePolicy,
    GameMode,
    GameState,
    Move,
    Player,
)


@dataclass(frozen=True, slots=True)
class CreateGameRequest:
    mode: GameMode = GameMode.TWO_PLAYER
    forbidden_move_policy: ForbiddenMovePolicy = ForbiddenMovePolicy.OFF


@dataclass(frozen=True, slots=True)
class MoveRequest:
    x: int
    y: int
    expected_revision: int | None = None

    def to_domain(self) -> Move:
        return Move(x=self.x, y=self.y)


@dataclass(frozen=True, slots=True)
class CpuMoveRequest:
    expected_revision: int


@dataclass(frozen=True, slots=True)
class GameResponse:
    id: str
    board: Board
    current_player: Player
    status: str
    winner: Player | None
    mode: str
    revision: int
    forbidden_move_policy: str
    result_reason: str | None

    @classmethod
    def from_state(cls, game_id: UUID, state: GameState) -> "GameResponse":
        return cls(
            id=str(game_id),
            board=state.board,
            current_player=state.current_player,
            status=state.status.value,
            winner=state.winner,
            mode=state.mode.value,
            revision=state.revision,
            forbidden_move_policy=state.forbidden_move_policy.value,
            result_reason=state.result_reason.value
            if state.result_reason is not None
            else None,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    error: str
    reason: str | None = None

    def to_dict(self) -> dict[str, str]:
        result = {"error": self.error}
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class CsrfResponse:
    detail: str = "CSRF cookie set"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
