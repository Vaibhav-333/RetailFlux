"""Request-ID middleware — stamps every request/response with a correlation UUID."""
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

X_REQUEST_ID = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    For every inbound request:
      1. Read ``X-Request-ID`` from headers (if present) or generate a fresh UUID.
      2. Bind the ID to structlog's context-local variables so every log line in
         this request's coroutine includes ``request_id``.
      3. Echo the ID back in the response ``X-Request-ID`` header for client-side
         log correlation.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get(X_REQUEST_ID) or str(uuid.uuid4())

        # Bind to structlog context for the lifetime of this coroutine
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()

        response.headers[X_REQUEST_ID] = request_id
        return response
