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

# This needs Python 3.10 for your local runtime environment

# Select an NVIDIA base image with desired GPU stack from https://ngc.nvidia.com/catalog/containers/nvidia:cuda
FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

WORKDIR /workspace

COPY requirements_gemma_2b.txt requirements.txt
COPY setup.py /workspace/
COPY pyproject.toml /workspace/
COPY beamllm /workspace/

RUN \
    apt-get update && apt upgrade -y \
    && apt-get install -y curl \
        python3.10 \
        python3.10-venv \
        python3-venv \
        # With python3.10 package, distutils need to be installed separately.
        python3-distutils \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.10 10 \
    && curl https://bootstrap.pypa.io/get-pip.py | python \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e . \
    && rm -f requirements.txt

# clean up
RUN rm -fr setup.py pyproject.toml beamllm

# Copy model
COPY model_files/gemma_instruct_2b_en.keras /workspace/

ENV KERAS_BACKEND="tensorflow"

# Copy files from official SDK image, including script/dependencies.
COPY --from=apache/beam_python3.10_sdk:${BEAM_VERSION} /opt/apache/beam /opt/apache/beam

# Set the entrypoint to Apache Beam SDK launcher.
ENTRYPOINT ["/opt/apache/beam/boot"]