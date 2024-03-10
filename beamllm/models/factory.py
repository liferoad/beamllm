# Beam LLM
from beamllm.models.base import LLM


class LLMFactory:
    def __init__(self):
        self._models = {}

    def register_model(self, name: str, model: LLM):
        self._models[name.lower()] = model

    def get_model(self, name: str) -> LLM:
        if name.lower() in self._models:
            return self._models[name.lower()]
        else:
            raise ValueError(f"Model {name} not found")
