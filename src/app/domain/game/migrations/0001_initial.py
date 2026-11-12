import uuid

from django.db import migrations, models

import app.domain.game.model.board_constraint
import app.domain.game.service.game_service


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "board",
                    models.JSONField(
                        default=app.domain.game.service.game_service.initialize_board
                    ),
                ),
                ("current_player", models.PositiveSmallIntegerField(default=1)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("in_progress", "In progress"),
                            ("won", "Won"),
                            ("draw", "Draw"),
                        ],
                        default="in_progress",
                        max_length=16,
                    ),
                ),
                (
                    "winner",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "games"},
        ),
        migrations.AddConstraint(
            model_name="game",
            constraint=app.domain.game.model.board_constraint.board_constraint(),
        ),
        migrations.AddConstraint(
            model_name="game",
            constraint=models.CheckConstraint(
                condition=models.Q(current_player__in=(1, 2)),
                name="game_current_player_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="game",
            constraint=models.CheckConstraint(
                condition=models.Q(status__in=("in_progress", "won", "draw")),
                name="game_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="game",
            constraint=models.CheckConstraint(
                condition=models.Q(winner__isnull=True) | models.Q(winner__in=(1, 2)),
                name="game_winner_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="game",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(status="won", winner__isnull=False, winner__in=(1, 2))
                    | models.Q(status__in=("in_progress", "draw"), winner__isnull=True)
                ),
                name="game_status_winner_consistent",
            ),
        ),
    ]
