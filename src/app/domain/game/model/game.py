import uuid

from django.db import models
from django.db.models import Q

from app.domain.game.model.board_constraint import board_constraint
from app.domain.game.service.game_service import initialize_board


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games"
        constraints = [
            board_constraint(),
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
