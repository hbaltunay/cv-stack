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

from app.api.v1.schemas.serve import ServeResponse
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.services import cache_service, triton_service
from app.utils.image import image_hash

router = APIRouter(prefix="/serve", tags=["serve"])
logger = get_logger("cvs")


@router.post(
    "",
    response_model=ServeResponse,
)
async def serve(
    request: Request,
    _response: Response,
    file: Annotated[UploadFile, File()],
    model_name: Annotated[str, Form()],
    _user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> ServeResponse:

    image_bytes = await file.read()

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size cannot exceed 10MB",
        )

    image_key = image_hash(image_bytes)

    cached = await cache_service.get(f"SERVE:{model_name}:{image_key}")

    if cached is not None:
        return ServeResponse(
            model_name=model_name,
            request_id=request.state.request_id,
            status="Cached",
            results=cached["results"],
        )

    results = await triton_service.serve(
        model_name=model_name,
        image_bytes=image_bytes,
        request_id=request.state.request_id,
    )

    await cache_service.set(
        key=f"SERVE:{model_name}:{image_key}",
        value={"status": "Completed", "results": results},
    )

    return ServeResponse(
        model_name=model_name,
        request_id=request.state.request_id,
        status="Completed",
        results=results,
    )
