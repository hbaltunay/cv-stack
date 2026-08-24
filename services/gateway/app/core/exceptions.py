from fastapi import HTTPException, status


class DetailedHTTPException(HTTPException):
    STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR
    DETAIL = "An error occurred on the server."

    def __init__(self, detail: str = None) -> None:
        super().__init__(
            status_code=self.STATUS_CODE, detail=detail or self.DETAIL
        )


class TritonServiceException(DetailedHTTPException):
    STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE
    DETAIL = "Triton AI service error."


class CacheServiceException(DetailedHTTPException):
    STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE
    DETAIL = "Redis cache service error."


class QueueServiceException(DetailedHTTPException):
    STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE
    DETAIL = "Kafka queue service error."
