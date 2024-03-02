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
from apache_beam.io import PubsubMessage
from apache_beam.ml.inference.base import KeyedModelHandler, PredictionResult, RunInference
from apache_beam.ml.inference.pytorch_inference import PytorchModelHandlerTensor, make_tensor_model_fn
from transformers import AutoConfig, AutoModelForSeq2SeqLM, AutoTokenizer

# Beam LLM
from beamllm.config import ModelConfig, ModelName, SinkConfig, SourceConfig

MAX_RESPONSE_TOKENS = 256

model_name = "google/flan-t5-small"
state_dict_path = "gs://xqhu-ml/llm-models/flan-t5-small.pt"


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


def build_pipeline(pipeline, source_config: SourceConfig, sink_config: SinkConfig, model_config: ModelConfig) -> None:
    """
    Args:
      pipeline: a given input pipeline
      source_config: a source config
      sink_config: a sink config
      model_config: a model config to instantiate PytorchModelHandlerTensor
    """

    if model_config.name == ModelName.FLAN_T5_SMALL:
        # Load the tokenizer.
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Create an instance of the PyTorch model handler.
        model_handler = KeyedModelHandler(
            PytorchModelHandlerTensor(
                state_dict_path=state_dict_path,
                model_class=AutoModelForSeq2SeqLM.from_config,
                model_params={"config": AutoConfig.from_pretrained(model_name)},
                inference_fn=make_tensor_model_fn("generate"),
            )
        )
    else:
        raise ValueError("Only support google/flan-t5-small now!")

    _ = (
        pipeline
        | "ReadFromPubSub" >> beam.io.ReadFromPubSub(topic=source_config.input, with_attributes=True)
        | "PreprocessData" >> beam.Map(lambda x: (x.attributes.get("id"), x.data.decode("utf-8")))
        | "ConvertNumpyToTensor" >> beam.Map(lambda x: (x[0], tokenizer(x[1], return_tensors="pt").input_ids[0]))
        | "RunInference"
        >> RunInference(
            model_handler,
            inference_args={"max_new_tokens": MAX_RESPONSE_TOKENS},
        )
        | "PostProcessPredictions" >> beam.ParDo(PredictionWithKeyProcessor(tokenizer))
        | "EncodeWithAttributes"
        >> beam.Map(lambda x: PubsubMessage(data=x[1].encode("utf-8"), attributes={"id": x[0]}))
        | "Write to PubSub" >> beam.io.WriteToPubSub(topic=sink_config.output, with_attributes=True)
    )
