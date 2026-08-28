from app.models.user import User
from app.schemas.auth import PublicUserResponse


def to_public_user(user: User) -> PublicUserResponse:
    return PublicUserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )
