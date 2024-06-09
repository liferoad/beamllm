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

SILENT:
.PHONY:
.DEFAULT_GOAL := help

# Load environment variables from .env file
include .env
export

define PRINT_HELP_PYSCRIPT
import re, sys # isort:skip

matches = []
for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		matches.append(match.groups())

for target, help in sorted(matches):
    print("     %-25s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

PYTHON = python$(PYTHON_VERSION)

help: ## Print this help
	@echo
	@echo "  make targets:"
	@echo
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

init-venv: ## Create virtual environment in venv folder
	@$(PYTHON) -m venv venv

init: init-venv ## Init virtual environment
	@./venv/bin/python3 -m pip install -U pip
	@$(shell sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g" requirements.prod.txt > requirements.txt)
	@./venv/bin/python3 -m pip install -r requirements.txt
	@./venv/bin/python3 -m pip install -r requirements.dev.txt
	@./venv/bin/python3 -m pre_commit install --install-hooks --overwrite
	@mkdir -p beam-output
	@echo "use 'source venv/bin/activate' to activate venv "
	@./venv/bin/python3 -m pip install -e .

format: ## Run formatter on source code
	@./venv/bin/python3 -m black --config=pyproject.toml .

lint: ## Run linter on source code
	@./venv/bin/python3 -m black --config=pyproject.toml --check .
	@./venv/bin/python3 -m flake8 --config=.flake8 .

clean-lite: ## Remove pycache files, pytest files, etc
	@rm -rf build dist .cache .coverage .coverage.* *.egg-info
	@find . -name .coverage | xargs rm -rf
	@find . -name .pytest_cache | xargs rm -rf
	@find . -name .tox | xargs rm -rf
	@find . -name __pycache__ | xargs rm -rf
	@find . -name *.egg-info | xargs rm -rf

clean: clean-lite ## Remove virtual environment, downloaded models, etc
	@rm -rf venv
	@echo "run 'make init'"

docker_t5: ## Build the docker with the t5 model and push it to Artifact Registry
	$(shell sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g; s|\$${PYTHON_VERSION}|$(PYTHON_VERSION)|g" containers/flan_t5/flan_t5_small_gpu.Dockerfile > Dockerfile)
	@rm -f requirements_t5.txt
	@sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g" containers/flan_t5/requirements_t5.txt > requirements_t5.txt
	docker build --platform linux/amd64 -t $(CUSTOM_CONTAINER_IMAGE_ROOT)/flan_t5_small:gpu -f Dockerfile .
	docker push $(CUSTOM_CONTAINER_IMAGE_ROOT)/flan_t5_small:gpu
	@rm -f requirements_t5.txt

docker_gemma_2b: ## Build the docker with the gemma 2b model and push it to Artifact Registry
	$(shell sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g; s|\$${PYTHON_VERSION}|$(PYTHON_VERSION)|g" containers/gemma_2b/gemma_2b_gpu.Dockerfile > Dockerfile)
	@rm -f requirements_gemma_2b.txt
	@sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g" containers/gemma_2b/requirements_gemma_2b.txt > requirements_gemma_2b.txt
	docker build --platform linux/amd64 -t $(CUSTOM_CONTAINER_IMAGE_ROOT)/gemma_2b:gpu -f Dockerfile .
	docker push $(CUSTOM_CONTAINER_IMAGE_ROOT)/gemma_2b:gpu
	@rm -f requirements_gemma_2b.txt

docker_ollama: ## Build the docker with ollama and push it to Artifact Registry
	$(shell sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g; s|\$${PYTHON_VERSION}|$(PYTHON_VERSION)|g" containers/ollama/ollama.Dockerfile > Dockerfile)
	@rm -f requirements_ollama.txt
	@sed "s|\$${BEAM_VERSION}|$(BEAM_VERSION)|g" containers/ollama/requirements_ollama.txt > requirements_ollama.txt
	docker build --platform linux/amd64 -t $(CUSTOM_CONTAINER_IMAGE_ROOT)/ollama:latest -f Dockerfile .
	docker push $(CUSTOM_CONTAINER_IMAGE_ROOT)/ollama:latest
	@rm -f requirements_ollama.txt

run-gpu: ## Run a Dataflow job with GPUs
	$(eval JOB_NAME := beam-llm-$(shell date +%s)-$(shell echo $$$$))
	time ./venv/bin/python3 -m beamllm.run \
	--runner DataflowRunner \
	--job_name $(JOB_NAME) \
	--project $(PROJECT_ID) \
	--region $(REGION) \
	--machine_type $(MACHINE_TYPE) \
	--disk_size_gb $(DISK_SIZE_GB) \
	--staging_location $(STAGING_LOCATION) \
	--temp_location $(TEMP_LOCATION) \
	--setup_file ./setup.py \
	--device GPU \
	--dataflow_service_option $(SERVICE_OPTIONS) \
	--number_of_worker_harness_threads 1 \
	--experiments=disable_worker_container_image_prepull \
	--sdk_container_image $(CUSTOM_CONTAINER_IMAGE_ROOT)/$(MODEL_TAG) \
	--sdk_location container \
	--experiments=use_pubsub_streaming \
	--model_name $(MODEL_NAME) \
	--max_response $(MAX_RESPONSE) \
	--ollama_model_name $(OLLAMA_MODEL_NAME) \
	--input projects/$(PROJECT_ID)/topics/$(INPUT_TOPIC) \
	--output projects/$(PROJECT_ID)/topics/$(OUTPUT_TOPIC)

run-chat: ## Start chatting
	@./venv/bin/python3 beamllm/chat.py
