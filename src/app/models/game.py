import uuid

from django.db import models
from django.db.models import Q


def empty_board() -> list[list[int]]:
    """Return a fresh empty 15 by 15 board for a new game."""
    return [[0 for _ in range(15)] for _ in range(15)]


class Game(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        WON = "won", "Won"
        DRAW = "draw", "Draw"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.JSONField(default=empty_board)
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
                    Q(status="won", winner__in=(1, 2))
                    | Q(status__in=("in_progress", "draw"), winner__isnull=True)
                ),
                name="game_status_winner_consistent",
            ),
        ]

    def __str__(self) -> str:
        return f"Game {self.pk} ({self.status})"
