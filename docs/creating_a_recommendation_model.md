# Creating a Recommendation Model

## Step 1: Create a New Model File
1. Navigate to the `app/recommendations/` directory.
3. Add a new Python file for your model (e.g., `your_new_model.py`).

## Step 2: Implement the Model
Your model must inherit from `BaseRecommender` and implement the following methods:
- `load_data`: Load and preprocess the training data.
- `train`: Train the model.
- `predict`: Generate predictions for user input.

## Step 3: Adjust the `app.py` Imports
Once the model's created and you're sure that it's an improvement over the last model, adjust the import in [`app.py`](../app/app.py) to use that model.

## Step 4: Push Your Model
Once you create a pull request to merge into main, any models will be evaluated. If merged, the best model (within the entire repository) will be deployed automatically.

### Example
For a detailed example of this, see the implementation of [Andres' recommender](../app/recommendations/CourseRecommender.py) that matches user input to a course from a Kaggle dataset. 