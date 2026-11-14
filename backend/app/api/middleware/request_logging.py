import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path,
                   "status": response.status_code, "duration_ms": duration},
        )
        return response
