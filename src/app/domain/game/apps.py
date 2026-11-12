from django.apps import AppConfig


class GomokuConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.domain.game"

    def import_models(self) -> None:
        super().import_models()
        from app.domain.game.model import game  # noqa: F401
