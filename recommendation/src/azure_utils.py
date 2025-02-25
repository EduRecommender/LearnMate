from azureml.core import Workspace, Experiment, Model, Dataset
import os
import pandas as pd
from dotenv import load_dotenv

def get_workspace():
    """Retrieve the AzureML workspace using environment variables.
    
    This function connects to the AzureML workspace based on the settings from the environment variables.
    Ensure the environment variables AZURE_WORKSPACE_NAME, AZURE_SUBSCRIPTION_ID, and AZURE_RESOURCE_GROUP
    are set before calling this function.

    Returns:
        Workspace: The AzureML workspace object.
    """

    load_dotenv()
    ws = Workspace.get(
        name=os.getenv("AZURE_WORKSPACE_NAME"),
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group=os.getenv("AZURE_RESOURCE_GROUP"),
    )
    return ws


def start_experiment(experiment_name, ws=None):
    """Start an AzureML experiment to track training results.

    This function initializes an experiment and starts logging for tracking training runs.
    
    Args:
        experiment_name (str): The name of the experiment to create or attach to.
        ws (Workspace, optional): The AzureML workspace object. If None, it will use the default workspace.
    
    Returns:
        Run: The run object that logs the experiment's details.
    """
    if ws is None:
        ws = get_workspace()  # Use default workspace if not provided

    experiment = Experiment(ws, experiment_name)
    run = experiment.start_logging()
    return run


def save_and_register(model, model_name, model_path, description, ws=None):
    """Save and register a model in AzureML.

    This function saves the given model to the specified path and registers it with AzureML for future use.
    
    Args:
        model (sklearn.base.BaseEstimator or any model object): The model object to save and register.
        model_name (str): The name for the registered model.
        model_path (str): The local path where the model should be saved.
        description (str): A description of the model to be registered.
        ws (Workspace, optional): The AzureML workspace object. If None, it will use the default workspace.
    
    Returns:
        Model: The registered model object.
    """
    if ws is None:
        ws = get_workspace()  # Use default workspace if not provided
    
    model.save(model_path)
    registered_model = Model.register(
        workspace=ws,
        model_name=model_name,
        model_path=model_path,
        description=description
    )
    return registered_model


def get_dataset(dataset_name, version=None, ws=None):
    """Retrieve a registered dataset from AzureML by name and version.

    This function fetches a dataset from AzureML by its name and optionally its version.

    Args:
        dataset_name (str): The name of the dataset to retrieve.
        version (str or None, optional): The version of the dataset to retrieve. If None, the latest version is used.
        ws (Workspace, optional): The AzureML workspace object. If None, it will use the default workspace.

    Returns:
        Dataset: The requested dataset object.
    """
    if ws is None:
        ws = get_workspace()  # Use default workspace if not provided

    dataset = Dataset.get_by_name(ws, dataset_name, version=version)
    return dataset
