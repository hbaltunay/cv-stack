import asyncio
from typing import Any

import numpy as np
import tritonclient.grpc.aio as grpcclient
from numpy.typing import NDArray
from tritonclient.grpc import InferInput, InferRequestedOutput, InferResult
from tritonclient.utils import InferenceServerException

from app.core.config import get_settings
from app.core.exceptions import TritonServiceException
from app.core.logging import get_logger
from app.core.telemetry import observe

settings = get_settings()
logger = get_logger("cvs")

TRITON_DTYPE_MAP: dict[int, str] = {
    1: "BOOL",
    2: "UINT8",
    3: "UINT16",
    4: "UINT32",
    5: "UINT64",
    6: "INT8",
    7: "INT16",
    8: "INT32",
    9: "INT64",
    10: "FP16",
    11: "FP32",
    12: "FP64",
    13: "BYTES",
    14: "BF16",
}

NUMPY_DTYPE_MAP: dict[str, type] = {
    "BOOL": np.bool_,
    "UINT8": np.uint8,
    "UINT16": np.uint16,
    "UINT32": np.uint32,
    "UINT64": np.uint64,
    "INT8": np.int8,
    "INT16": np.int16,
    "INT32": np.int32,
    "INT64": np.int64,
    "FP16": np.float16,
    "FP32": np.float32,
    "FP64": np.float64,
    "BF16": np.float32,
}


class TritonService:
    def __init__(self) -> None:
        self._client: grpcclient.InferenceServerClient | None = None
        self._model_configs: dict[str, dict[str, Any]] = {}

    @property
    def client(self) -> grpcclient.InferenceServerClient:
        if self._client is None:
            err_msg = "Triton client is not initialized. Call start() first."
            raise TritonServiceException(detail=f"Triton Error: {err_msg}")

        return self._client

    async def start(self) -> None:
        try:
            self._client = grpcclient.InferenceServerClient(
                url=f"{settings.TRITON_HOST}:{settings.TRITON_PORT}"
            )

            repo = await self._client.get_model_repository_index()

            for model in repo.models:
                config = await self._client.get_model_config(model.name)
                inputs = [
                    {
                        "name": i.name,
                        "dtype": TRITON_DTYPE_MAP.get(i.data_type, "FP32"),
                        "shape": list(i.dims),
                    }
                    for i in config.config.input
                ]
                outputs = [
                    {
                        "name": o.name,
                        "dtype": TRITON_DTYPE_MAP.get(o.data_type, "FP32"),
                        "shape": list(o.dims),
                    }
                    for o in config.config.output
                ]
                self._model_configs[model.name] = {
                    "inputs": inputs,
                    "outputs": outputs,
                }
                logger.info(
                    f"Model config loaded: {model.name} | inputs={inputs} | "
                    f"outputs={outputs}",
                )

            logger.info("Triton Server Inference Starting.")

        except Exception as err:
            logger.error(f"Failed to load model configs: {err}")
            raise TritonServiceException(detail=f"Triton Error: {err}") from err

    async def shutdown(self) -> None:
        try:
            await self._client.close()
            self._client = None

            logger.info("Triton connection has been terminated.")

        except Exception as err:
            logger.warning("Triton connection could not be terminated.")
            raise TritonServiceException(detail=f"Triton Error: {err}") from err

    async def health_check(self) -> bool:
        try:
            return await self.client.is_server_live()
        except Exception as err:
            logger.error(
                "Triton health check error",
                extra={"params": {"error": str(err)}},
            )
            raise TritonServiceException(detail=f"Triton Error: {err}") from err

    async def _get_model_config(self, model_name: str) -> dict[str, Any]:
        if model_name in self._model_configs:
            return self._model_configs[model_name]

        config = await self.client.get_model_config(model_name)

        self._model_configs[model_name] = {
            "inputs": [
                {
                    "name": i.name,
                    "dtype": TRITON_DTYPE_MAP.get(i.data_type, "FP32"),
                    "shape": list(i.dims),
                }
                for i in config.config.input
            ],
            "outputs": [
                {
                    "name": o.name,
                    "dtype": TRITON_DTYPE_MAP.get(o.data_type, "FP32"),
                    "shape": list(o.dims),
                }
                for o in config.config.output
            ],
        }

        logger.info(
            "Model configuration loaded.",
            extra={"params": {"model_name": model_name}},
        )

        return self._model_configs[model_name]

    def _preprocess(
        self,
        config: dict[str, Any],
        input_values: list[NDArray],
    ) -> tuple[list[InferInput], list[InferRequestedOutput]]:

        inputs = []

        for i, input_array in enumerate(input_values):
            cfg = config["inputs"][i]
            name, _, datatype = cfg["name"], cfg["shape"], cfg["dtype"]
            infer_input = grpcclient.InferInput(
                name, input_array.shape, datatype
            )
            infer_input.set_data_from_numpy(input_array)
            inputs.append(infer_input)

        outputs = [
            grpcclient.InferRequestedOutput(o["name"])
            for o in config["outputs"]
        ]

        return inputs, outputs

    def _postprocess(
        self, config: dict[str, Any], response: InferResult
    ) -> dict[str, Any]:
        return {
            o["name"]: response.as_numpy(o["name"]).tolist()
            for o in config["outputs"]
        }

    @observe(name="Triton", method="Infer")
    async def infer(
        self,
        model_name: str,
        input_values: list[NDArray],
        request_id: str,
    ) -> dict[str, Any]:
        try:
            params = {"model_name": model_name, "request_id": request_id}

            config = await self._get_model_config(model_name)

            inputs, outputs = self._preprocess(config, input_values)

            response = await self.client.infer(
                model_name=model_name,
                inputs=inputs,
                outputs=outputs,
                client_timeout=settings.TRITON_TIMEOUT,
            )

            results = self._postprocess(config, response)

            logger.info("Triton inference completed", extra={"params": params})

            return {
                "model_name": model_name,
                "results": results,
            }

        except InferenceServerException as e:
            logger.error("Triton inference error", extra={"params": params})
            raise TritonServiceException(detail=f"Triton Error: {e}") from e

        except Exception as err:
            logger.error(
                "Unexpected error",
                extra={"params": {"error": str(err), **params}},
            )
            raise TritonServiceException(detail=f"Triton Error: {err}") from err

    @staticmethod
    def _convert(image_bytes: bytes) -> NDArray:
        nparr = np.frombuffer(image_bytes, dtype=np.uint8)
        return np.expand_dims([nparr], axis=0)

    @observe(name="Triton", method="Serve")
    async def serve(
        self,
        model_name: str,
        image_bytes: bytes,
        request_id: str,
    ) -> dict[str, Any]:
        try:
            input_values = await asyncio.to_thread(
                self._convert, image_bytes
            )

            return await self.infer(model_name, input_values, request_id)

        except Exception as err:
            raise TritonServiceException(detail=f"Triton Error: {err}") from err
