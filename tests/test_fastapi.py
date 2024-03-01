import logging
from typing import Iterator, Optional

import fastapi
import pytest
from fastapi.testclient import TestClient

from fastapi_errors import BaseHTTPError, register_errors


class AuthorizationError(BaseHTTPError):
    message = "Failed to authorize"
    status_code = fastapi.status.HTTP_401_UNAUTHORIZED

    async def hook(self, request: fastapi.Request) -> None:
        logging.log(logging.ERROR, self.message)


class InvalidRequestError(BaseHTTPError):
    message = "Invalid request"
    status_code = fastapi.status.HTTP_400_BAD_REQUEST


class NoUserFoundError(BaseHTTPError):
    message = "No such user"
    status_code = fastapi.status.HTTP_404_NOT_FOUND


def authorize(token: Optional[str] = fastapi.Header(None)):
    if token is None:
        raise AuthorizationError(
            reason="no token",
        )
    if token != "TOKEN":
        raise AuthorizationError(
            reason="no token",
            token=token,  # Don't do that.
        )


router = fastapi.APIRouter(
    dependencies=[
        fastapi.Depends(authorize),
    ],
)


@router.get("/")
@router.get("/{user}")
def get_user(user: Optional[str] = None):
    if user is None:
        raise InvalidRequestError(reason="no user")
    if "user" not in user:
        raise NoUserFoundError(user=user)
    return {"user": user}


@pytest.fixture()
def app() -> Iterator[fastapi.FastAPI]:
    app = fastapi.FastAPI()

    app.include_router(router)

    register_errors(
        app,
        [
            AuthorizationError,
            InvalidRequestError,
            NoUserFoundError,
        ],
    )

    yield app


@pytest.fixture()
def client(app: fastapi.FastAPI) -> TestClient:
    return TestClient(app)


def test_get_user_no_token(client: TestClient) -> None:
    r = client.get("/user-1")
    assert r.status_code == AuthorizationError.status_code
    assert r.json() == AuthorizationError(reason="no token").to_dict()


def test_get_user_invalid_token(client: TestClient) -> None:
    token = "?"

    r = client.get(
        "/user-1",
        headers={"token": token},
    )
    assert r.status_code == AuthorizationError.status_code
    assert r.json() == AuthorizationError(reason="no token", token=token).to_dict()


def test_get_no_user(client: TestClient) -> None:
    r = client.get(
        "/",
        headers={"token": "TOKEN"},
    )
    assert r.status_code == InvalidRequestError.status_code
    assert r.json() == InvalidRequestError(reason="no user").to_dict()


def test_get_invalid_user(client: TestClient) -> None:
    user = "1"

    r = client.get(
        f"/{user}",
        headers={"token": "TOKEN"},
    )
    assert r.status_code == NoUserFoundError.status_code
    assert r.json() == NoUserFoundError(user=user).to_dict()


def test_get_user(client: TestClient) -> None:
    user = "user-1"

    r = client.get(
        f"/{user}",
        headers={"token": "TOKEN"},
    )
    assert r.status_code == fastapi.status.HTTP_200_OK
    assert r.json() == {"user": user}
