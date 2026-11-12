"""PostgreSQL JSONPath expressions for board integrity."""

from django.db import models
from django.db.models.functions import Cast
from django.db.models.lookups import Contains


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
            # JSONB preserves decimal scale when rendered as text; JSONPath's
            # numeric comparisons alone consider 1 and 1.0 equal.
            & ~Contains(Cast(models.F("board"), models.TextField()), models.Value("."))
        ),
        name="game_board_valid",
    )
