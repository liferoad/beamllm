# standard libraries
from abc import ABC, abstractmethod


class LLM(ABC):
    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    def get_pipeline(self):
        pass
