from azureml.core import Workspace

ws = Workspace.from_config()
print(f"Connected to workspace: {ws.name}")