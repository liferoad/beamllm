# third party libraries
import apache_beam as beam
import numpy as np
from apache_beam.ml.inference import utils
from apache_beam.ml.inference.base import KeyedModelHandler, RunInference
from apache_beam.ml.inference.tensorflow_inference import TFModelHandlerNumpy

# Beam LLM
from beamllm.config import ModelConfig
from beamllm.models.base import LLM


class PredictionWithKeyProcessorGemma(beam.DoFn):
    def process(self, element, *args, **kwargs):
        key = element[0]
        # input_value = element[1].example
        output_value = element[1].inference
        yield (key, output_value)


def gemma_inference_function(model, batch, inference_args, model_id):
    vectorized_batch = np.stack(batch, axis=0)
    # The only inference_arg expected here is a max_length parameter to
    # determine how many words are included in the output.
    predictions = model.generate(vectorized_batch, **inference_args)
    return utils._convert_to_result(batch, predictions, model_id)


class Gemma(LLM):
    def __init__(
        self,
        name="google/flan-t5-small",
        path="gs://xqhu-ml/llm-models/gemma_instruct_2b_en.keras",
    ):
        """Only init model information here"""
        self._name = name
        self._path = path

    def load_model(self, model_config: ModelConfig):
        """Load the model (expensive)"""
        self._inference_args = {"max_length": model_config.max_response}

        # Specify the model handler, providing a path and the custom inference function.
        self._model_handler = KeyedModelHandler(
            TFModelHandlerNumpy(
                self._path,
                inference_fn=gemma_inference_function,
                device=model_config.device,
                large_model=True,
            )
        )

    def get_pipeline(self):
        return "RunInferenceGemma" >> RunInference(
            self._model_handler, inference_args=self._inference_args
        ) | "PostProcessPredictionsGemma" >> beam.ParDo(PredictionWithKeyProcessorGemma())
