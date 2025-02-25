import json

def init():
    print("Skip loading for now to avoid issues.")

def run(raw_data):
    """
    Runs the recommendation model and returns the recommendations.
    
    TODO: Complete this function
    This is just a skeleton function at this point to avoid issues with Azure deployment.

    Args:
        raw_data (str): The raw input data as a JSON string. Expected format:
            {
                "input": "I want to learn programming basics"
            }

    Returns:
        recommendations (JSON): JSON representing the recommendations made by the model.
            Example:
            {
                "recommendations": [
                    {
                        "Name": "Introduction to Programming",
                        "University": "Stanford University",
                        "Link": "https://example.com",
                        "Category": "Programming"
                    },
                    ...
                ]
            }
    """
    return json.dumps({"recommendations": {
                        "Name": "Introduction to Programming",
                        "University": "Stanford University",
                        "Link": "https://example.com",
                        "Category": "Programming"
                    }})
