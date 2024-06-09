# standard libraries
from collections.abc import Iterable, Sequence
from typing import Any, Dict, Optional

# third party libraries
import apache_beam as beam
import ollama
from apache_beam.ml.inference.base import KeyedModelHandler, ModelHandler, PredictionResult, RunInference

# Beam LLM
from beamllm.config import ModelConfig
from beamllm.models.base import LLM


class PredictionWithKeyProcessorOllama(beam.DoFn):
    def process(self, element, *args, **kwargs):
        key = element[0]
        # input_value = element[1].example
        output_value = element[1].inference
        yield (key, output_value)


class OllamaModelHandler(ModelHandler[str, PredictionResult, str]):
    def __init__(
        self,
        model_name: str = "llama3",
    ):
        """Implementation of the ModelHandler interface for ollama using text as input.

        Example Usage::

          pcoll | RunInference(OllamaModelHandler())

        Args:
          model_name: The ollama model name. Default is llama3. The list can be found at https://ollama.com/library.
        """
        self._model_name = model_name
        self._env_vars = {}

    def load_model(self) -> str:
        """Loads and initializes a model for processing."""
        ollama.pull(self._model_name)
        return ollama.show(self._model_name)

    def run_inference(
        self, batch: Sequence[str], model: str, inference_args: Optional[Dict[str, Any]] = None
    ) -> Iterable[PredictionResult]:
        """Runs inferences on a batch of text strings.

        Args:
          batch: A sequence of examples as text strings.
          model: A ollama model. This is only a placeholder.
          inference_args: Any additional arguments for an inference.

        Returns:
          An Iterable of type PredictionResult.
        """
        # Loop each text string, and use a tuple to store the inference results.
        predictions = []
        for one_text in batch:
            response = ollama.chat(
                model=self._model_name,
                messages=[
                    {
                        "role": "user",
                        "content": one_text,
                    },
                ],
            )
            predictions.append([response["message"]["content"]])
        return [PredictionResult(x, y) for x, y in zip(batch, predictions)]


class Ollama(LLM):
    def __init__(
        self,
        name="ollama",
        path="/workspace/llama3",
    ):
        """Only init model information here"""
        self._name = name
        self._path = path

    def load_model(self, model_config: ModelConfig):
        """Load the model (expensive)"""

        # Specify the model handler, providing a path and the custom inference function.
        self._model_handler = KeyedModelHandler(
            OllamaModelHandler(
                model_name=model_config.ollama_model_name,
            )
        )

    def get_pipeline(self):
        return "RunInferenceGemma" >> RunInference(self._model_handler) | "PostProcessPredictionsGemma" >> beam.ParDo(
            PredictionWithKeyProcessorOllama()
        )
