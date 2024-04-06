# standard libraries
from typing import Tuple

# third party libraries
import apache_beam as beam
from apache_beam.ml.inference.base import KeyedModelHandler, PredictionResult, RunInference
from apache_beam.ml.inference.pytorch_inference import PytorchModelHandlerTensor, make_tensor_model_fn
from transformers import AutoConfig, AutoModelForSeq2SeqLM, AutoTokenizer

# Beam LLM
from beamllm.config import ModelConfig
from beamllm.models.base import LLM


class PredictionWithKeyProcessor(beam.DoFn):
    """Process the keyed results"""

    def __init__(self, tokenizer):
        self._tokenizer = tokenizer
        beam.DoFn.__init__(self)

    def process(self, element: Tuple[str, PredictionResult]):
        key = element[0]
        # input_value = element[1].example
        output_value = element[1].inference
        yield (key, self._tokenizer.decode(output_value, skip_special_tokens=True))


class FlanT5(LLM):
    def __init__(
        self,
        name="google/flan-t5-small",
        path="gs://xqhu-ml/llm-models/flan-t5-small.pt",
    ):
        """Only init model information here"""
        self._name = name
        self._path = path

    def load_model(self, model_config: ModelConfig):
        """Load the model (expensive)"""
        # Load the tokenizer.
        self._tokenizer = AutoTokenizer.from_pretrained(self._name)

        self._inference_args = {"max_new_tokens": model_config.max_response}

        # Create an instance of the PyTorch model handler.
        self._model_handler = KeyedModelHandler(
            PytorchModelHandlerTensor(
                state_dict_path=self._path,
                model_class=AutoModelForSeq2SeqLM.from_config,
                model_params={"config": AutoConfig.from_pretrained(self._name)},
                device=model_config.device,
                inference_fn=make_tensor_model_fn("generate"),
            )
        )

    def get_pipeline(self):
        return (
            "ConvertNumpyToTensor"
            >> beam.Map(lambda x: (x[0], self._tokenizer(x[1], return_tensors="pt").input_ids[0]))
            | "RunInferenceWithFlanT5" >> RunInference(self._model_handler, inference_args=self._inference_args)
            | "PostProcessPredictions" >> beam.ParDo(PredictionWithKeyProcessor(self._tokenizer))
        )
