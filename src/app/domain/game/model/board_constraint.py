"""PostgreSQL JSONPath expressions for board integrity."""

from django.db import models
from django.db.models.functions import Cast


class JsonPathField(models.Field):
    def db_type(self, connection):
        return "jsonpath"


def board_constraint() -> models.CheckConstraint:
    def exists(path: str) -> models.Func:
        return models.Func(
            models.F("board"),
            Cast(models.Value(path), output_field=JsonPathField()),
            function="jsonb_path_exists",
            output_field=models.BooleanField(),
        )

    return models.CheckConstraint(
        condition=(
            exists('strict $ ? (@.type() == "array" && @.size() == 15)')
            & ~exists('strict $[*] ? (@.type() != "array" || @.size() != 15)')
            & ~exists(
                'strict $[*][*] ? (@.type() != "number" || (@!=0 && @!=1 && @!=2))'
            )
        ),
        name="game_board_valid",
    )
