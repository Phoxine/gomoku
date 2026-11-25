"""Framework-independent game state and move contracts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, TypeAlias

Player: TypeAlias = Literal[1, 2]
Cell: TypeAlias = Literal[0, 1, 2]
Board: TypeAlias = list[list[Cell]]


class GameStatus(StrEnum):
    """Lifecycle states shared by the game domain and persistence layer."""

    IN_PROGRESS = "in_progress"
    WON = "won"
    DRAW = "draw"


class GameMode(StrEnum):
    TWO_PLAYER = "two_player"
    CPU = "cpu"


@dataclass(slots=True)
class GameState:
    """Mutable rule-relevant game data, without persistence metadata."""

    board: Board
    current_player: Player
    status: GameStatus
    winner: Player | None = None
    mode: GameMode = GameMode.TWO_PLAYER

    @property
    def revision(self) -> int:
        return sum(len(row) - row.count(0) for row in self.board)


@dataclass(frozen=True, slots=True)
class Move:
    """A requested board position; the active player comes from GameState."""

    x: int
    y: int


class IllegalMoveReason(StrEnum):
    """Stable machine-readable reasons for rejected move commands."""

    INVALID_COORDINATE = "invalid_coordinate"
    OUT_OF_BOUNDS = "out_of_bounds"
    OCCUPIED = "occupied"
    GAME_FINISHED = "game_finished"
    INVALID_REQUEST = "invalid_request"
    NOT_HUMAN_TURN = "not_human_turn"
    STALE_REVISION = "stale_revision"
    NOT_CPU_GAME = "not_cpu_game"


class IllegalMoveError(ValueError):
    """Expected domain error raised when a move cannot be applied."""

    def __init__(self, reason: IllegalMoveReason) -> None:
        self.reason = reason
        super().__init__(reason.value)
