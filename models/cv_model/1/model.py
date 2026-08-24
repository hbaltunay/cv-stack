import logging
from typing import Any

import numpy as np
import triton_python_backend_utils as pb_utils
from c_python_backend_utils import (
    InferenceRequest,
    InferenceResponse,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


OUTPUT_DATA = np.array(
    [
        [0.0, 0.0, 0.5, 0.5, 0.9, 0.0],
        [0.5, 0.5, 0.5, 0.5, 0.9, 0.0],
    ],
    dtype=np.float32,
)


class TritonPythonModel:
    def initialize(self, args: dict[str, Any]) -> None:
        pass

    def execute(
        self, requests: list[InferenceRequest]
    ) -> list[InferenceResponse]:

        responses = []
        for request in requests:
            input_tensor = pb_utils.get_input_tensor_by_name(request, "input_0")

            logger.info(
                f"Input Tensor Shape: {(input_tensor.as_numpy().shape)}"  # noqa
            )

            out_tensor = pb_utils.Tensor("output_0", OUTPUT_DATA)

            inference_response = pb_utils.InferenceResponse(
                output_tensors=[out_tensor]
            )
            responses.append(inference_response)

        return responses

    def finalize(self) -> None:
        pass
