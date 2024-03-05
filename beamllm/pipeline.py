#  Copyright 2023 Google LLC

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""A pipeline that uses RunInference API to perform image classification."""

# standard libraries
from typing import Tuple

# third party libraries
import apache_beam as beam
import numpy as np
from apache_beam.io import PubsubMessage
from apache_beam.ml.inference import utils
from apache_beam.ml.inference.base import KeyedModelHandler, PredictionResult, RunInference
from apache_beam.ml.inference.pytorch_inference import PytorchModelHandlerTensor, make_tensor_model_fn
from apache_beam.ml.inference.tensorflow_inference import TFModelHandlerNumpy
from transformers import AutoConfig, AutoModelForSeq2SeqLM, AutoTokenizer

# Beam LLM
from beamllm.config import ModelConfig, ModelName, SinkConfig, SourceConfig, model_location

MAX_RESPONSE_TOKENS = 256


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


def build_pipeline(pipeline, source_config: SourceConfig, sink_config: SinkConfig, model_config: ModelConfig) -> None:
    """
    Args:
      pipeline: a given input pipeline
      source_config: a source config
      sink_config: a sink config
      model_config: a model config to instantiate PytorchModelHandlerTensor
    """

    preprocess = (
        pipeline
        | "ReadFromPubSub" >> beam.io.ReadFromPubSub(topic=source_config.input, with_attributes=True)
        | "PreprocessData" >> beam.Map(lambda x: (x.attributes.get("id"), x.data.decode("utf-8")))
    )

    if model_config.name == ModelName.FLAN_T5_SMALL:
        model_name = "google/flan-t5-small"
        state_dict_path = model_location.get(ModelName.FLAN_T5_SMALL)
        # Load the tokenizer.
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Create an instance of the PyTorch model handler.
        model_handler = KeyedModelHandler(
            PytorchModelHandlerTensor(
                state_dict_path=state_dict_path,
                model_class=AutoModelForSeq2SeqLM.from_config,
                model_params={"config": AutoConfig.from_pretrained(model_name)},
                device=model_config.device,
                inference_fn=make_tensor_model_fn("generate"),
            )
        )

        pred = (
            preprocess
            | "ConvertNumpyToTensor" >> beam.Map(lambda x: (x[0], tokenizer(x[1], return_tensors="pt").input_ids[0]))
            | "RunInference"
            >> RunInference(model_handler, inference_args={"max_new_tokens": model_config.max_response})
            | "PostProcessPredictions" >> beam.ParDo(PredictionWithKeyProcessor(tokenizer))
        )
    elif model_config.name == ModelName.GEMMA_INSTRUCT_2B_EN:
        model_path = model_location.get(ModelName.GEMMA_INSTRUCT_2B_EN)
        # Specify the model handler, providing a path and the custom inference function.
        model_handler = KeyedModelHandler(
            TFModelHandlerNumpy(
                model_path,
                inference_fn=gemma_inference_function,
                device=model_config.device,
                large_model=True,
            )
        )

        pred = (
            preprocess
            | "RunInferenceGemma"
            >> RunInference(model_handler, inference_args={"max_length": model_config.max_response})
            | "PostProcessPredictionsGemma" >> beam.ParDo(PredictionWithKeyProcessorGemma())
        )
    else:
        raise ValueError("Only support google/flan-t5-small now!")

    _ = (
        pred
        | "EncodeWithAttributes"
        >> beam.Map(lambda x: PubsubMessage(data=x[1].encode("utf-8"), attributes={"id": x[0]}))
        | "Write to PubSub" >> beam.io.WriteToPubSub(topic=sink_config.output, with_attributes=True)
    )
