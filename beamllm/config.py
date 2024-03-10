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

# standard libraries
from enum import Enum

# third party libraries
from pydantic import BaseModel, Field


class ModelName(str, Enum):
    FLAN_T5_SMALL = "FLAN-T5-small"
    GEMMA_INSTRUCT_2B_EN = "gemma_instruct_2b_en"


class ModelConfig(BaseModel):
    name: ModelName = Field(ModelName.GEMMA_INSTRUCT_2B_EN, description="LLM model name")
    device: str = Field("CPU", description="Device to be used on the Runner. Choices are (CPU, GPU)")
    min_batch_size: int = 10
    max_batch_size: int = 100
    max_response: int = 256


class SourceConfig(BaseModel):
    input: str = Field(..., description="the input Pub/Sub topic")
    streaming: bool = True


class SinkConfig(BaseModel):
    output: str = Field(..., description="the output Pub/Sub topic")
