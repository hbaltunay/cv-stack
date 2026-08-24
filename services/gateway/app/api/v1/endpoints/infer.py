from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)

from app.api.v1.schemas.infer import InferResponse
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.services import cache_service, queue_service
from app.utils.image import image_hash

router = APIRouter(prefix="/infer", tags=["infer"])
logger = get_logger("cvs")


@router.post(
    "",
    response_model=InferResponse,
)
async def infer(
    request: Request,
    response: Response,
    file: Annotated[UploadFile, File()],
    model_name: Annotated[str, Form()],
    _user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> InferResponse:

    params = {
        "request_id": request.state.request_id,
        "model_name": model_name,
    }

    image_bytes = await file.read()

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size cannot exceed 10MB",
        )

    image_key = image_hash(image_bytes)

    cached = await cache_service.get(f"INFER:{model_name}:{image_key}")

    if cached is not None:
        response.status_code = status.HTTP_202_ACCEPTED

        return InferResponse(
            model_name=model_name,
            request_id=request.state.request_id,
            status="Cached",
            results=cached,
        )

    queue_service.publish(
        topic="infer-topic",
        image_bytes=image_bytes,
        model_name=model_name,
        request_id=request.state.request_id,
        image_key=image_key,
    )

    await cache_service.set(
        key=f"INFER:{model_name}:{image_key}",
        value={"status": "Queued", **params},
    )
    response.status_code = status.HTTP_202_ACCEPTED

    return InferResponse(
        model_name=model_name,
        request_id=request.state.request_id,
        status="Queued",
    )


@router.get(
    "/result",
    response_model=InferResponse,
)
async def get_result(request_id: str) -> InferResponse:
    result = await cache_service.get_result(f"Result:{request_id}")

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No results found. request_id may be invalid or expired.",
        )

    return InferResponse(**result)
