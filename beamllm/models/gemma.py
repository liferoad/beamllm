# standard libraries
from collections.abc import Iterable, Sequence
from typing import Any, Optional

# third party libraries
import apache_beam as beam
import keras_nlp
from apache_beam.ml.inference import utils
from apache_beam.ml.inference.base import KeyedModelHandler, ModelHandler, PredictionResult, RunInference
from keras_nlp.src.models.gemma.gemma_causal_lm import GemmaCausalLM

# Beam LLM
from beamllm.config import ModelConfig
from beamllm.models.base import LLM


class PredictionWithKeyProcessorGemma(beam.DoFn):
    def process(self, element, *args, **kwargs):
        key = element[0]
        # input_value = element[1].example
        output_value = element[1].inference
        yield (key, output_value)


class GemmaModelHandler(ModelHandler[str, PredictionResult, GemmaCausalLM]):
    def __init__(self, model_name: str = "gemma_2B", inference_args: Optional[dict[str, Any]] = None):
        """Implementation of the ModelHandler interface for Gemma using text as input.

        https://github.com/GoogleCloudPlatform/python-docs-samples/blob/main/dataflow/gemma/custom_model_gemma.py

        Args:
          model_name: The Gemma model name. Default is gemma_2B.
        """
        self._model_name = model_name
        self._inference_args = inference_args
        self._env_vars = {}

    def share_model_across_processes(self) -> bool:
        """Indicates if the model should be loaded once-per-VM rather than
        once-per-worker-process on a VM. Because Gemma is a large language model,
        this will always return True to avoid OOM errors.
        """
        return True

    def load_model(self) -> GemmaCausalLM:
        """Loads and initializes a model for processing."""
        return keras_nlp.models.GemmaCausalLM.from_preset(self._model_name)

    def run_inference(
        self, batch: Sequence[str], model: GemmaCausalLM, inference_args: Optional[dict[str, Any]] = None
    ) -> Iterable[PredictionResult]:
        """Runs inferences on a batch of text strings.

        Args:
          batch: A sequence of examples as text strings.
          model: The Gemma model being used.
          inference_args: Any additional arguments for an inference.

        Returns:
          An Iterable of type PredictionResult.
        """
        # Loop each text string, and use a tuple to store the inference results.
        predictions = []
        for one_text in batch:
            result = model.generate(one_text, **self._inference_args)
            predictions.append(result)
        return utils._convert_to_result(batch, predictions, self._model_name)


class Gemma(LLM):
    def __init__(
        self,
        name="gemma_instruct_2b_en",
        path="/workspace/gemma_instruct_2b_en",
    ):
        """Only init model information here"""
        self._name = name
        self._path = path

    def load_model(self, model_config: ModelConfig):
        """Load the model (expensive)"""
        self._inference_args = {"max_length": model_config.max_response}

        # Specify the model handler, providing a path and the custom inference function.
        self._model_handler = KeyedModelHandler(
            GemmaModelHandler(
                model_name=self._path,
                inference_args=self._inference_args,
            )
        )

    def get_pipeline(self):
        return "RunInferenceGemma" >> RunInference(self._model_handler) | "PostProcessPredictionsGemma" >> beam.ParDo(
            PredictionWithKeyProcessorGemma()
        )
