from django.db import models
from django.db.models import Q

from app.domain.game.model.game import Game


class GameMove(models.Model):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="moves",
        db_index=False,
    )
    move_number = models.SmallIntegerField()
    player = models.SmallIntegerField()
    x = models.SmallIntegerField()
    y = models.SmallIntegerField()

    class Meta:
        db_table = "game_moves"
        constraints = [
            models.CheckConstraint(
                condition=Q(move_number__range=(1, 225)),
                name="game_move_number_valid",
            ),
            models.CheckConstraint(
                condition=Q(player__in=(1, 2)),
                name="game_move_player_valid",
            ),
            models.CheckConstraint(
                condition=Q(x__range=(0, 14)),
                name="game_move_x_valid",
            ),
            models.CheckConstraint(
                condition=Q(y__range=(0, 14)),
                name="game_move_y_valid",
            ),
            models.UniqueConstraint(
                fields=("game", "move_number"),
                name="game_move_number_unique",
            ),
            models.UniqueConstraint(
                fields=("game", "x", "y"),
                name="game_move_position_unique",
            ),
        ]
