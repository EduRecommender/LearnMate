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
        
        subscription_id = os.getenv("AZURE_ML_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_ML_RESOURCE_GROUP")
        workspace_name = os.getenv("AZURE_ML_WORKSPACE_NAME")
        
        if not all([subscription_id, resource_group, workspace_name]):
            raise ValueError("Missing Azure ML environment variables: AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME")
        
        self.ws = Workspace(
            subscription_id=subscription_id,
            resource_group=resource_group,
            workspace_name=workspace_name
        )

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

    def register_model(self, feedback_metrics=None):
        """Register the model and feedback metrics in Azure ML."""
        if not self.is_trained:
            raise ValueError("Model must be trained before registering")
            
        experiment = Experiment(self.ws, "LearnMate_Evaluation")
        with experiment.start_logging() as run:
            run.log("model_name", self.model_name)
            run.log("version", self.version)
            run.log("training_date", datetime.now().isoformat())
            
            if feedback_metrics:
                for metric, value in feedback_metrics.items():
                    run.log(metric, value)
            
            model_path = "model.pkl"
            azure_model = Model.register(
                workspace=self.ws,
                model_path=model_path,
                model_name=self.model_name,
                tags={
                    "version": self.version,
                    "metrics": str(feedback_metrics) if feedback_metrics else None,
                    "training_date": datetime.now().isoformat()
                }
            )
            print(f"Model registered in Azure ML: {azure_model.name}, version {azure_model.version}")