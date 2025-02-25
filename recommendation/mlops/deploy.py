import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri("sqlite:///mlflow.db")

def get_best_model():
    
    """Gets the best model from the currently trained models, based on NDCG@K
    
    Returns:
        run_id (string) : Run ID of best model
        ndcg (double) : NDCG score of best model
    """

    client = MlflowClient()

    experiment = client.get_experiment_by_name("learnmate_recommendations")
    if experiment is None:
        raise ValueError("Experiment 'learnmate_recommendations' does not exist. Please ensure it is created.")

    runs = client.search_runs(experiment.experiment_id, order_by=["metrics.ndcgk DESC"])
    
    if not runs:
        raise ValueError("No runs found in the experiment.")
    
    # Get the best run
    best_run = runs[0]
    return best_run.info.run_id, best_run.data.metrics["ndcgk"]

def deploy_model(run_id):
    """Deploy the model. This is a skeleton function but we can configure it once we decide on a deployment platform.
    
    Args:
        run_id (string): String containing Run ID
    """
    print(f"Deploying model from run {run_id}")

if __name__ == "__main__":
    run_id, ndcg = get_best_model()
    print(f"Best model has NDCG: {ndcg}")
    deploy_model(run_id)