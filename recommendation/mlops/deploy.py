import mlflow
from mlflow.tracking import MlflowClient

def get_best_model():
    client = MlflowClient()
    experiment = client.get_experiment_by_name("learnmate_recommendations")
    runs = client.search_runs(experiment.experiment_id, order_by=["metrics.ndcg DESC"])
    best_run = runs[0]
    return best_run.info.run_id, best_run.data.metrics["ndcg"]

def deploy_model(run_id):
    """Deploy the model. This is a skeleton function but we can configure it once we decide on a deployment platform.
    
        Args:
            run_id (string) : String containing Run ID
        
    """
    print(f"Deploying model from run {run_id}")

if __name__ == "__main__":
    run_id, ndcg = get_best_model()
    print(f"Best model has NDCG: {ndcg}")
    deploy_model(run_id)