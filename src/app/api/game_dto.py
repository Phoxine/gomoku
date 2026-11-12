"""Request and response data for game endpoints."""

from dataclasses import asdict, dataclass
from uuid import UUID

from app.domain.game.state import Board, GameState, Move, Player


@dataclass(frozen=True, slots=True)
class MoveRequest:
    x: int
    y: int

    def to_domain(self) -> Move:
        return Move(x=self.x, y=self.y)


@dataclass(frozen=True, slots=True)
class GameResponse:
    id: str
    board: Board
    current_player: Player
    status: str
    winner: Player | None

    @classmethod
    def from_state(cls, game_id: UUID, state: GameState) -> "GameResponse":
        return cls(
            id=str(game_id),
            board=state.board,
            current_player=state.current_player,
            status=state.status.value,
            winner=state.winner,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
