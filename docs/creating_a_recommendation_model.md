# Creating a Recommendation Model

## Step 1: Create a New Model File
1. Navigate to the `recommendation/models/team_models/` directory.
2. Create a new folder with your name (e.g., `/team_models/your_name`).
3. Add a new Python file for your model (e.g., `your_recommendation_model.py`).

## Step 2: Implement the Model
Your model must inherit from `BaseRecommender` and implement the following methods:
- `load_data`: Load and preprocess the training data.
- `train`: Train the model.
- `load_test_data`: Load and preprocess the training data.
- `predict`: Generate predictions for user input.
- `evaluate`: Evaluate the model using test data and return a dictionary with values for `precisionk`, `recallk`, and `ndcgk`.

## Step 3: Push your Model
Once you create a pull request to merge into main, any models will be evaluated. If merged, the best model (within the entire repository) will be deployed automatically.

### Example
For a detailed example of this, see the implementation of [Andres' recommender](../recommendation/models/team_models/Andres/CourseRecommenderCosine.py) that matches user input to a course from a Kaggle dataset. 