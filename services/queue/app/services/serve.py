from typing import Any

import tritonclient.grpc.aio as grpcclient
from numpy.typing import NDArray
from tritonclient.grpc import InferInput, InferRequestedOutput, InferResult
from tritonclient.utils import InferenceServerException

from app.core.config import get_settings
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
    "BOOL": bool,
    "UINT8": int,
    "UINT16": int,
    "UINT32": int,
    "UINT64": int,
    "INT8": int,
    "INT16": int,
    "INT32": int,
    "INT64": int,
    "FP16": float,
    "FP32": float,
    "FP64": float,
    "BF16": float,
}


class TritonService:
    def __init__(self) -> None:
        self._client: grpcclient.InferenceServerClient | None = None
        self._model_configs: dict[str, dict[str, Any]] = {}

    @property
    def client(self) -> grpcclient.InferenceServerClient:
        if self._client is None:
            raise RuntimeError(
                "Triton client is not initialized. Call start() first."
            )

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

        except Exception as e:
            logger.error(f"Failed to load model configs: {e}")
            raise

    async def shutdown(self) -> None:
        await self._client.close()
        self._client = None

        logger.info("Triton connection has been terminated.")

    async def health_check(self) -> bool:
        try:
            return await self.client.is_server_live()
        except Exception as e:
            logger.error(
                "Triton health check error",
                extra={"params": {"error": str(e)}},
            )
            return False

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
                "status": "Completed",
                "results": results,
            }

        except InferenceServerException:
            logger.error("Triton inference error", extra={"params": params})
            raise
        except Exception as e:
            logger.error(
                "Unexpected error",
                extra={"params": {"error": str(e), **params}},
            )
            raise
