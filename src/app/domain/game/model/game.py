import uuid

from django.db import models
from django.db.models import Q

from app.domain.game.model.board_constraint import board_constraint
from app.domain.game.service.game_service import initialize_board
from app.domain.game.state import (
    ForbiddenMovePolicy,
    ForbiddenMoveReason,
    GameMode,
    GameResultReason,
)


class Game(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        WON = "won", "Won"
        DRAW = "draw", "Draw"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.JSONField(default=initialize_board)
    current_player = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    winner = models.PositiveSmallIntegerField(null=True, blank=True)
    mode = models.CharField(
        max_length=16,
        choices=[(mode.value, mode.name) for mode in GameMode],
        default=GameMode.TWO_PLAYER.value,
        db_default=GameMode.TWO_PLAYER.value,
    )
    forbidden_move_policy = models.CharField(
        max_length=4,
        choices=[(policy.value, policy.name) for policy in ForbiddenMovePolicy],
        default=ForbiddenMovePolicy.OFF.value,
        db_default=ForbiddenMovePolicy.OFF.value,
    )
    result_reason = models.CharField(
        max_length=19,
        choices=[(reason.value, reason.name) for reason in GameResultReason],
        null=True,
        blank=True,
    )
    history_start_revision = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games"
        constraints = [
            board_constraint(),
            models.CheckConstraint(
                condition=Q(history_start_revision__range=(0, 225)),
                name="game_history_start_revision_valid",
            ),
            models.CheckConstraint(
                condition=Q(mode__in=tuple(mode.value for mode in GameMode)),
                name="game_mode_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    forbidden_move_policy__in=tuple(
                        policy.value for policy in ForbiddenMovePolicy
                    )
                ),
                name="game_forbidden_move_policy_valid",
            ),
            models.CheckConstraint(
                condition=Q(result_reason__isnull=True)
                | (
                    Q(status="won", winner=2, winner__isnull=False)
                    & (
                        Q(
                            forbidden_move_policy=ForbiddenMovePolicy.LOSS.value,
                            current_player=1,
                            result_reason__in=tuple(
                                reason.value for reason in ForbiddenMoveReason
                            ),
                        )
                        | Q(
                            forbidden_move_policy=ForbiddenMovePolicy.WARN.value,
                            current_player=2,
                            result_reason=GameResultReason.NO_LEGAL_BLACK_MOVE.value,
                        )
                    )
                ),
                name="game_forbidden_result_consistent",
            ),
            models.CheckConstraint(
                condition=Q(current_player__in=(1, 2)),
                name="game_current_player_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("in_progress", "won", "draw")),
                name="game_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(winner__isnull=True) | Q(winner__in=(1, 2)),
                name="game_winner_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="won", winner__isnull=False, winner__in=(1, 2))
                    | Q(status__in=("in_progress", "draw"), winner__isnull=True)
                ),
                name="game_status_winner_consistent",
            ),
        ]

    def __str__(self) -> str:
        return f"Game {self.pk} ({self.status})"
