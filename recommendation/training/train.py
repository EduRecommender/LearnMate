import os
import importlib
from recommendation.mlops.model_registry import mlflow

def discover_models():
    """Find all of the models located in the team_models directory."""

    models = []
    team_models_dir = os.path.join("recommendation", "models", "team_models")
    for teammate in os.listdir(team_models_dir):
        teammate_dir = os.path.join(team_models_dir, teammate)
        if os.path.isdir(teammate_dir):
            for model_file in os.listdir(teammate_dir):
                if model_file.endswith("py") and model_file != "__init__.py":
                    model_name = model_file[:-3]
                    module_path = f"recommendation.models.team_models.{teammate}.{model_name}"
                    models.append((teammate, model_name, module_path))
    return models

def train_and_log_models():
    """Trains and logs all models using their own methods."""
    models = discover_models()
    for teammate, model_name, module_path in models:
        print(f"Training {model_name} by {teammate}")
        module = importlib.import_module(module_path)
        model_class = getattr(module, model_name)
        model = model_class()
        model.load_data()
        model.train()
        model.load_test_data()

        # Evalute the model and log the results
        eval_results = model.evaluate()
        model.log_model(evaluation_results=eval_results)

if __name__ == "__main__":
    train_and_log_models()
