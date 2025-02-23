from abc import ABC, abstractmethod
import mlflow
from datetime import datetime

class BaseRecommender(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.version = datetime.now().strftime("%Y%m%d_%H%M")
        self.is_trained = False

    @abstractmethod
    def load_data(self):
        """Load the training data used by this model."""

    @abstractmethod
    def train(self, data):
        pass

    @abstractmethod
    def predict(self, data):
        pass

    def log_model(self):
        if not self.is_trained:
            raise ValueError("Model must be trained before logging")
        
        with mlflow.start_run(run_name=f"{self.model_name}_{self.version}"):
            mlflow.sklearn.log_model(
                self,
                f"{self.model_name}_{self.version}",
                registered_model_name=self.model_name
            )
