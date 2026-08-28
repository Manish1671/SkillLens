from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    create_token_with_expiry,
    hash_password,
)
from fastapi.testclient import TestClient


def register_payload(email: str, password: str = "password123", name: str = "Test User") -> dict:
    return {"email": email, "password": password, "display_name": name}


def login_payload(email: str, password: str = "password123") -> dict:
    return {"email": email, "password": password}


def test_register_success(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=register_payload("new@example.com"))
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["display_name"] == "Test User"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email(client: TestClient) -> None:
    email = "duplicate@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    response = client.post("/api/auth/register", json=register_payload(email))
    assert response.status_code == 409
    assert response.json()["code"] == "email_already_exists"


def test_password_is_hashed(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "hashed@example.com"
    password = "password123"
    client.post("/api/auth/register", json=register_payload(email, password))
    user = UserRepository().find_by_email(db_session, email)
    assert user is not None
    assert user.password_hash != password
    assert user.password_hash.startswith("$argon2")


def test_plaintext_password_not_stored(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "plain@example.com"
    password = "password123"
    client.post("/api/auth/register", json=register_payload(email, password))
    user = UserRepository().find_by_email(db_session, email)
    assert user is not None
    assert password not in user.password_hash


def test_login_success_sets_cookies(client: TestClient) -> None:
    email = "login@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    response = client.post("/api/auth/login", json=login_payload(email))
    assert response.status_code == 200
    assert settings.access_cookie_name in response.cookies
    assert settings.refresh_cookie_name in response.cookies


def test_login_wrong_password(client: TestClient) -> None:
    email = "wrongpass@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    response = client.post("/api/auth/login", json=login_payload(email, "wrong-password"))
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_login_unknown_email(client: TestClient) -> None:
    response = client.post("/api/auth/login", json=login_payload("missing@example.com"))
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert response.json()["detail"] == "Invalid email or password"


def test_me_after_login(client: TestClient) -> None:
    email = "me@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    client.post("/api/auth/login", json=login_payload(email))
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_me_without_authentication(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_me_with_malformed_access_token(client: TestClient) -> None:
    client.cookies.set(settings.access_cookie_name, "not-a-jwt")
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_me_with_expired_access_token(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "expired-access@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    user = UserRepository().find_by_email(db_session, email)
    expired = create_token_with_expiry(
        user.id,
        TOKEN_TYPE_ACCESS,
        datetime.now(UTC) - timedelta(minutes=1),
    )
    client.cookies.set(settings.access_cookie_name, expired)
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_refresh_success(client: TestClient) -> None:
    email = "refresh@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    login_response = client.post("/api/auth/login", json=login_payload(email))
    client.cookies.clear()
    client.cookies.set(
        settings.refresh_cookie_name, login_response.cookies[settings.refresh_cookie_name]
    )
    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
    assert settings.access_cookie_name in response.cookies
    assert settings.refresh_cookie_name in response.cookies


def test_refresh_malformed_token(client: TestClient) -> None:
    client.cookies.set(settings.refresh_cookie_name, "bad-token")
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401


def test_refresh_expired_token(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "expired-refresh@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    user = UserRepository().find_by_email(db_session, email)
    expired = create_token_with_expiry(
        user.id,
        TOKEN_TYPE_REFRESH,
        datetime.now(UTC) - timedelta(days=1),
    )
    client.cookies.set(settings.refresh_cookie_name, expired)
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401


def test_refresh_token_rejected_as_access_token(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "refresh-as-access@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    user = UserRepository().find_by_email(db_session, email)
    refresh_token = create_refresh_token(user.id)
    client.cookies.set(settings.access_cookie_name, refresh_token)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_access_token_rejected_in_refresh_flow(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "access-as-refresh@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    user = UserRepository().find_by_email(db_session, email)
    access_token = create_access_token(user.id)
    client.cookies.set(settings.refresh_cookie_name, access_token)
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_logout_clears_authentication(client: TestClient) -> None:
    email = "logout@example.com"
    client.post("/api/auth/register", json=register_payload(email))
    client.post("/api/auth/login", json=login_payload(email))
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401


def test_user_lookup_by_id(client: TestClient, db_session) -> None:
    from app.repositories.user_repository import UserRepository

    email = "lookup@example.com"
    register_response = client.post("/api/auth/register", json=register_payload(email))
    user_id = register_response.json()["id"]
    user = UserRepository().find_by_id(db_session, user_id)
    assert user is not None
    assert user.email == email


def test_user_data_cannot_cross_account_boundaries(client: TestClient) -> None:
    client.post("/api/auth/register", json=register_payload("usera@example.com", name="User A"))
    client.post("/api/auth/register", json=register_payload("userb@example.com", name="User B"))
    client.post("/api/auth/login", json=login_payload("usera@example.com"))
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "usera@example.com"
    assert me_response.json()["display_name"] == "User A"


def test_auth_full_flow(client: TestClient) -> None:
    email = "flow@example.com"
    register = client.post("/api/auth/register", json=register_payload(email))
    assert register.status_code == 201
    login = client.post("/api/auth/login", json=login_payload(email))
    assert login.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    refresh = client.post("/api/auth/refresh")
    assert refresh.status_code == 200
    me_after_refresh = client.get("/api/auth/me")
    assert me_after_refresh.status_code == 200
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    me_after_logout = client.get("/api/auth/me")
    assert me_after_logout.status_code == 401


def test_hash_password_unit() -> None:
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert hashed.startswith("$argon2")
