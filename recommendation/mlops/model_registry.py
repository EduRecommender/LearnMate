import mlflow

mlflow.set_tracking_uri("sqlite:/mlflow.db")
mlflow.set_experiment("learnmate_recommendations")
