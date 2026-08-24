import os
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.infer import router as infer_router
from app.api.v1.endpoints.serve import router as serve_router
from app.api.v1.endpoints.stream import router as stream_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.telemetry import setup_telemetry
from app.middleware.error_handler import register_middleware
from app.services import (
    cache_service,
    queue_service,
    stream_service,
    triton_service,
)

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger("cvs")

setup_telemetry()

cache_statu = settings.REDIS_ENABLED
serve_statu = settings.TRITON_ENABLED
queue_statu = settings.QUEUE_ENABLED
stream_statu = settings.STREAM_ENABLED


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    if serve_statu:
        await triton_service.start()
    if cache_statu:
        await cache_service.start()
    if queue_statu:
        queue_service.start()
    if stream_statu:
        await stream_service.start()

    yield

    if serve_statu:
        await triton_service.shutdown()
    if cache_statu:
        await cache_service.shutdown()
    if queue_statu:
        queue_service.shutdown()
    if stream_statu:
        await stream_service.shutdown()


app = FastAPI(lifespan=lifespan)
register_middleware(app)

# Routers
app.include_router(infer_router, prefix="/api/v1/endpoints")
app.include_router(stream_router, prefix="/api/v1/endpoints")
app.include_router(serve_router, prefix="/api/v1/endpoints")
app.include_router(health_router, prefix="/api/v1/endpoints")


@app.get("/")
async def read() -> dict[str, str]:
    return {"message": "Triton Server Inference Starting.."}


@app.get("/reset/process")
async def reset_process() -> dict[str, str]:
    executable = sys.executable
    args = sys.argv
    os.execv(executable, [executable] + args)

    return {"message": "The server has been restarted."}


@app.get("/reset/worker")
async def reset_worker() -> dict[str, str]:
    os.kill(os.getppid(), signal.SIGHUP)

    return {"message": "The server has been restarted."}


# trace_info = TraceInfo()


# @app.get("/trace")
# async def log_trace(trace_id: str) -> dict[str, str]:
#     trace_info.log(trace_id)
#     return {"message": "Successfull"}
