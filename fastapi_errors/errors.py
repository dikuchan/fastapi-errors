from typing import Any, Awaitable, Callable, ClassVar, Dict, Iterable, Optional, Type

from starlette.applications import Starlette
from starlette.exceptions import WebSocketException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.websockets import WebSocket

ERROR_TYPE_HEADER = "X-Error-Type"


class BaseHTTPError(Exception):
    status_code: ClassVar[int]
    message: ClassVar[str]

    def __init__(self, **context: Any) -> None:
        super().__init__(self.__class__.message)
        self.context = context

    def __str__(self) -> str:
        return f"{self.status_code}: {self.message}"

    def __repr__(self) -> str:
        return f"{self.name}(status_code={self.status_code!r}, message={self.message!r}, context={self.context!r})"

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "context": self.context,
        }

    def to_response(self, request: Request) -> Response:
        return JSONResponse(
            self.to_dict(),
            status_code=self.status_code,
            headers={
                ERROR_TYPE_HEADER: self.name,
            },
        )

    async def hook(self, request: Request) -> None:
        return


def create_http_error_handler() -> Callable[[Request, Exception], Awaitable[Response]]:
    async def handle_error(request: Request, error: Exception) -> Response:
        if not isinstance(error, BaseHTTPError):
            raise TypeError(f"Exception `{error.__class__.__name__}` should be derived from `{BaseHTTPError.__name__}`")

        await error.hook(request)
        return error.to_response(request)

    return handle_error


class BaseWebSocketError(Exception):
    code: ClassVar[int]
    reason: ClassVar[Optional[str]] = None

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __str__(self) -> str:
        return f"{self.code}: {self.reason}"

    def __repr__(self) -> str:
        return f"{self.name}(code={self.code!r}, reason={self.reason!r})"

    async def hook(self, websocket: WebSocket) -> None:
        return


def create_websocket_error_handler() -> Callable[[WebSocket, Exception], Awaitable[None]]:
    async def handle_error(websocket: WebSocket, error: Exception) -> None:
        if not isinstance(error, BaseWebSocketError):
            raise TypeError(
                f"Exception `{error.__class__.__name__}` should be derived from `{BaseWebSocketError.__name__}`"
            )

        await error.hook(websocket)
        raise WebSocketException(code=error.code, reason=error.reason)

    return handle_error


def register_errors(app: Starlette, error_classes: Iterable[Type[Exception]]) -> None:
    for error_cls in error_classes:
        if issubclass(error_cls, BaseHTTPError):
            app.add_exception_handler(
                error_cls,
                create_http_error_handler(),
            )
        elif issubclass(error_cls, BaseWebSocketError):
            app.add_exception_handler(
                error_cls,
                create_websocket_error_handler(),
            )
        else:
            raise TypeError(
                f"Exception `{error_cls.__name__} should be derived from either "
                + f"`{BaseHTTPError.__name__}` or `{BaseWebSocketError.__name__}`"
            )
