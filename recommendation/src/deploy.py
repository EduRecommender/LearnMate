import os
import shutil
from azureml.core import Model, Environment
from azureml.core.model import InferenceConfig
from azureml.core.webservice import AciWebservice
from azure_utils import get_workspace

def deploy_model(model_name, service_name):
    ws = get_workspace()

    # Full paths for model and data
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "model.pkl")
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "input_data", "kaggle_filtered_courses.csv")

    print(f"Model path: {model_path}")
    print(f"Data path: {data_path}")
    
    # We use a temp directory to copy the model .pkl file and the temp_data to make it easier for Azure's deployment
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_deploy")
    os.makedirs(temp_dir, exist_ok=True)
    temp_model_path = os.path.join(temp_dir, "model.pkl")
    temp_data_path = os.path.join(temp_dir, "kaggle_filtered_courses.csv")
    shutil.copy2(model_path, temp_model_path)
    shutil.copy2(data_path, temp_data_path)

    # Register model
    model = Model.register(
        workspace=ws,
        model_path=temp_dir,
        model_name=model_name,
        description="Course Recommender with data file",
        tags={"type": "recommendation"}
    )

    # AzureML requires that an environment be provided to specify dependencies
    env_path = os.path.join(os.path.dirname(__file__), "environment.yaml")
    env = Environment.from_conda_specification(
        name="course-recommender-env",
        file_path=env_path
    )
    env.register(workspace=ws)

    src_dir = os.path.dirname(__file__)

    # For now, we use a custom scoring method defined in 'score.py'
    # It's just a dummy scoring method until we determine the best method to evaluate models
    inference_config = InferenceConfig(
        entry_script="score.py",
        source_directory=src_dir,
        environment=env
    )

    # Configure deployment
    aci_config = AciWebservice.deploy_configuration(
        cpu_cores=1,
        memory_gb=1,
        tags={"model": model_name},
        description="Course Recommender Deployment"
    )

    # Deploy to Azure Container Instance (ACI)
    service = Model.deploy(
        workspace=ws,
        name=service_name,
        models=[model],
        inference_config=inference_config,
        deployment_config=aci_config,
        overwrite=True
    )
    
    try:
        service.wait_for_deployment(show_output=True)
        print(f"Deployed to {service.scoring_uri}")
        return service
    except Exception as e:
        logs = service.get_logs()
        print("Deployment Logs:")
        print(logs)
        raise e

if __name__ == "__main__":
    deploy_model(
        model_name="CourseRecommenderCosine",  # Name of the registered model
        service_name="course-recommender-service"  # Name of the deployment
    )