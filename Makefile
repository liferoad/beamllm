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

run-cpu: ## Run a Dataflow job
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
	--requirements_file ./requirements.txt \
	--device CPU \
	--experiments=use_pubsub_streaming \
	--input projects/$(PROJECT_ID)/topics/$(INPUT_TOPIC) \
	--output projects/$(PROJECT_ID)/topics/$(OUTPUT_TOPIC)

run-chat: ## Start chatting
	@./venv/bin/python3 beamllm/chat.py

test-pubsub: ## Test to send a Pub/Sub message and receive one
	gcloud pubsub topics publish $(INPUT_TOPIC) \
	--message "translate English to Spanish: We are in New York City." \
	--project $(PROJECT_ID)
	gcloud pubsub subscriptions pull --auto-ack $(OUTPUT_TOPIC)-sub --project $(PROJECT_ID)
