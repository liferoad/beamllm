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

"""A run module that runs a Beam pipeline to deploy LLM models."""

# standard libraries
import argparse
import logging

# third party libraries
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from apache_beam.runners.runner import PipelineResult

# Beam LLM
from beamllm.config import ModelConfig, SinkConfig, SourceConfig
from beamllm.pipeline import build_pipeline


def parse_known_args(argv):
    """Parses args for the workflow."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", dest="input", required=True, help="Input pub/sub topic")
    parser.add_argument("--output", dest="output", required=True, help="Output pub/sub topic")
    return parser.parse_known_args(argv)


def run(argv=None, save_main_session=True, test_pipeline=None) -> PipelineResult:
    """
    Args:
      argv: Command line arguments defined for this example.
      save_main_session: Used for internal testing.
      test_pipeline: Used for internal testing.
    """
    known_args, pipeline_args = parse_known_args(argv)

    # setup configs
    model_config = ModelConfig()
    source_config = SourceConfig(input=known_args.input)
    sink_config = SinkConfig(output=known_args.output)

    # setup pipeline
    pipeline_options = PipelineOptions(pipeline_args, streaming=source_config.streaming)
    pipeline_options.view_as(SetupOptions).save_main_session = save_main_session
    pipeline_options.view_as(SetupOptions).pickle_library = "cloudpickle"

    pipeline = test_pipeline
    if not test_pipeline:
        pipeline = beam.Pipeline(options=pipeline_options)

    # build the pipeline using configs
    build_pipeline(pipeline, source_config=source_config, sink_config=sink_config, model_config=model_config)

    # run it
    result = pipeline.run()
    return result


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
