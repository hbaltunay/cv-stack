import nvidia.dali as dali
import nvidia.dali.types as types
from nvidia.dali import pipeline_def
from nvidia.dali.data_node import DataNode


@pipeline_def(batch_size=32, num_threads=1, device_id=0)
def cv_pipeline() -> DataNode:

    images = dali.fn.external_source(device="cpu", name="DALI_INPUT_0")
    images = dali.fn.decoders.image(
        images, device="mixed", output_type=types.RGB
    )
    images = dali.fn.resize(images, resize_x=640, resize_y=640)
    return dali.fn.crop_mirror_normalize(
        images,
        dtype=types.FLOAT,
        output_layout="CHW",
        mean=[0.0, 0.0, 0.0],
        std=[255.0, 255.0, 255.0],
    )


if __name__ == "__main__":
    pipe = cv_pipeline()
    pipe.build()
    pipe.serialize(filename="model.dali")
