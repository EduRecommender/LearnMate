from abc import ABC, abstractmethod
import mlflow
from datetime import datetime

class BaseRecommender(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.version = datetime.now().strftime("%Y%m%d_%H%M")
        self.is_trained = False
        self.data = None
        self.test_data = None

    @abstractmethod
    def load_data(self):
        """
        Load and preprocess the training data. Each model implements its own logic.
        """
        pass

    @abstractmethod
    def train(self):
        """Train the model on the loaded data."""
        pass

    @abstractmethod
    def predict(self, user_data):
        """Generate predictions for the given user data."""
        pass

    def log_model(self, evaluation_results=None):
        """Log the model to Azure ML."""
        if not self.is_trained:
            raise ValueError("Model must be trained before logging")
            
        with mlflow.start_run(run_name=f"{self.model_name}_{self.version}"):
            mlflow.sklearn.log_model(
                self,
                f"{self.model_name}_{self.version}",
                registered_model_name=self.model_name
            )
            
            # Log evaluation metrics if provided
            if evaluation_results:
                for metric, value in evaluation_results.items():
                    mlflow.log_metric(metric, value)