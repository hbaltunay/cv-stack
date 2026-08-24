from typing import Any

from pydantic import BaseModel, field_validator


class ServeRequest(BaseModel):
    model_name: str
    inputs: list[list[float]]

    @field_validator("model_name")
    @classmethod
    def model_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model_name cannot be empty")
        return v

    @field_validator("inputs")
    @classmethod
    def inputs_not_empty(cls, v: list[list[float]]) -> list[list[float]]:
        if not v:
            raise ValueError("inputs cannot be empty")
        return v


class ServeResponse(BaseModel):
    model_name: str
    request_id: str
    status: str
    results: dict[str, Any] | None = None
