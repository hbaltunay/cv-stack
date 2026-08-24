import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import DetailedHTTPException
from app.core.logging import get_logger
from app.core.telemetry import observe, set_attributes

settings = get_settings()

logger = get_logger("cvs")


def register_middleware(app: FastAPI) -> None:

    @app.middleware("http")
    @observe(name="Gateway")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[JSONResponse]],
    ) -> JSONResponse:

        request_id: str = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        params = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "client_ip": request.client.host if request.client else None,
        }

        logger.info("Request completed", extra={"params": params})

        trace_id = set_attributes(
            {
                "http.request_id": request_id,
                "http.method": request.method,
                "http.url": str(request.url),
                "http.status_code": response.status_code,
            }
        )

        response.headers["X-Request-ID"] = request_id
        if settings.OTEL_ENABLED:
            response.headers["X-Trace-ID"] = trace_id

        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:

        request_id = getattr(request.state, "request_id", None)

        params = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
        }

        logger.info(exc)

        if isinstance(exc, DetailedHTTPException):
            logger.warning(
                f"Service exception: {exc.__class__.__name__}",
                extra={"params": params},
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "code": getattr(exc, "CODE", "SERVICE_ERROR"),
                    "request_id": request_id,
                },
            )

        logger.error(
            "Unhandled exception",
            exc_info=exc,
            extra={"params": params},
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "request_id": request_id,
            },
        )
