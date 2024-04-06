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

"""A pipeline that uses RunInference API to perform LLM chats."""

# third party libraries
import apache_beam as beam
from apache_beam.io import PubsubMessage

# Beam LLM
from beamllm.config import ModelConfig, SinkConfig, SourceConfig
from beamllm.models.factory import LLMFactory


def build_pipeline(
    pipeline,
    source_config: SourceConfig,
    sink_config: SinkConfig,
    model_config: ModelConfig,
    model_factory: LLMFactory,
) -> None:
    """
    Args:
      pipeline: a given input pipeline
      source_config: a source config
      sink_config: a sink config
      model_config: a model config to instantiate PytorchModelHandlerTensor
      model_factory: LLM factory
    """

    llm = model_factory.get_model(model_config.name)

    llm.load_model(model_config)

    # preprocess pub/sub messages
    preprocess = (
        pipeline
        | "ReadFromPubSub" >> beam.io.ReadFromPubSub(topic=source_config.input, with_attributes=True)
        | "PreprocessData" >> beam.Map(lambda x: (x.attributes.get("id"), x.data.decode("utf-8")))
    )

    # build the LLM pipeline
    pred = preprocess | llm.get_pipeline()

    # write the results to Pub/Sub with attributes
    _ = (
        pred
        | "EncodeWithAttributes"
        >> beam.Map(lambda x: PubsubMessage(data=x[1].encode("utf-8"), attributes={"id": x[0]}))
        | "Write to PubSub" >> beam.io.WriteToPubSub(topic=sink_config.output, with_attributes=True)
    )
