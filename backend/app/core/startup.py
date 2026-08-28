from app.core.config import settings

INSECURE_JWT_DEFAULT = "dev-only-change-in-production"


def validate_production_settings() -> None:
    if settings.app_env != "production":
        return
    if settings.jwt_secret_key == INSECURE_JWT_DEFAULT or len(settings.jwt_secret_key) < 32:
        raise RuntimeError(
            "Production requires a strong JWT_SECRET_KEY (32+ chars, not the dev default). "
            "Set JWT_SECRET_KEY in the environment before starting."
        )
