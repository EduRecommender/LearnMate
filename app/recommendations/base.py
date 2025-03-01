from abc import ABC, abstractmethod
from azureml.core import Workspace, Model, Run, Experiment
from datetime import datetime
import os
from dotenv import load_dotenv

class BaseRecommender(ABC):
    def __init__(self, model_name: str):
        load_dotenv()
        self.model_name = model_name
        self.version = datetime.now().strftime("%Y%m%d_%H%M")
        self.is_trained = False
        self.data = None

    @abstractmethod
    def load_data(self):
        """Load and preprocess the training data."""
        pass

    @abstractmethod
    def train(self):
        """Train the model on the loaded data."""
        pass

    @abstractmethod
    def predict(self, user_data):
        """Generate predictions for the given user data."""
        pass
