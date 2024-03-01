# flake8: noqa

from fastapi_errors.errors import (
    BaseHTTPError,
    BaseWebSocketError,
    create_http_error_handler,
    create_websocket_error_handler,
    register_errors,
)

create_http_exception_handler = create_http_error_handler
create_websocket_exception_handler = create_websocket_error_handler
register_exceptions = register_errors
