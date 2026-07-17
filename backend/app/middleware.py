from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class FrameAncestorsMiddleware(BaseHTTPMiddleware):
    """Set Content-Security-Policy: frame-ancestors on every response."""

    def __init__(self, app, value: str) -> None:
        super().__init__(app)
        self.value = value

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = f"frame-ancestors {self.value}"
        return response
