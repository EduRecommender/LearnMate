import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import ndcg_score
from azureml.core import Model
import joblib
from azure_utils import get_workspace

# Load and preprocess the training data
def load_data():
    data_path = os.path.join("input_data", "kaggle_filtered_courses.csv")
    data = pd.read_csv(data_path)
    data['Course Description'] = data['Course Description'].str.lower()
    data['About'] = data['About'].str.lower()
    data['combined_features'] = (
        data['Name'] + ' ' + data['About'] + ' ' + data['Course Description']
    )
    return data

# Load and preprocess the test data
def load_test_data():
    test_data = pd.DataFrame({
        'query': [
            "I want to learn programming basics",
            "I want to learn computer vision",
            "I want to learn data science"
        ],
        'ground_truth': [
            [1, 62, 137], 
            [382, 306],
            [309, 273]     
        ]
    })
    return test_data

# Train the TF-IDF vectorizer and compute the cosine similarity matrix
def train(data):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(data['combined_features'])
    return vectorizer, tfidf_matrix

# Recommend courses based on user input
def predict(user_input, data, vectorizer, tfidf_matrix, top_k=5, print_output=True):
    user_input = user_input.lower()
    user_tfidf = vectorizer.transform([user_input])
    user_cosine_sim = cosine_similarity(user_tfidf, tfidf_matrix)
    similar_indices = user_cosine_sim[0].argsort()[-top_k:][::-1]
    recommendations = data.iloc[similar_indices].copy()
    recommendations['Category'] = recommendations['Category'].astype(str)
    
    if print_output:
        print(recommendations[['Name', 'University', 'Link', 'Category']])
    
    return recommendations

# Evaluate the model
def evaluate(test_data, data, vectorizer, tfidf_matrix, top_k=5):
    precision_scores = []
    recall_scores = []
    ndcg_scores = []
    
    for _, row in test_data.iterrows():
        query = row['query']
        ground_truth = row['ground_truth']
        
        # Get recommendations
        recommendations = predict(query, data, vectorizer, tfidf_matrix, top_k, print_output=False)
        recommended_indices = recommendations.index.tolist()
        
        # Compute precision@k and recall@k
        relevant = set(ground_truth)
        retrieved = set(recommended_indices)
        precision = len(relevant.intersection(retrieved)) / top_k
        recall = len(relevant.intersection(retrieved)) / len(relevant) if len(relevant) > 0 else 0
        
        # Compute NDCG@k
        relevance_scores = [1 if idx in ground_truth else 0 for idx in recommended_indices]
        ndcg = ndcg_score([relevance_scores], [relevance_scores], k=top_k)
        
        precision_scores.append(precision)
        recall_scores.append(recall)
        ndcg_scores.append(ndcg)
    
    return {
        'precisionk': np.mean(precision_scores),
        'recallk': np.mean(recall_scores),
        'ndcgk': np.mean(ndcg_scores)
    }

# Main function to run the training and evaluation
def main():

    # Load data
    data = load_data()
    test_data = load_test_data()
    
    # Train the model
    vectorizer, tfidf_matrix = train(data)
    
    # Evaluate the model
    evaluation_results = evaluate(test_data, data, vectorizer, tfidf_matrix)
    print("Evaluation Results:", evaluation_results)
    
    # Save the model (e.g., using joblib or pickle)
    model_path = os.path.join(os.getcwd(), "model.pkl")
    joblib.dump((vectorizer, tfidf_matrix), model_path)
    
    # Register the model with Azure ML
    workspace = get_workspace()
    model = Model.register(workspace=workspace,
                           model_path=model_path,
                           model_name="CourseRecommenderCosine",
                           tags={"evaluation": evaluation_results},
                           description="Course Recommender using Cosine Similarity")
    print("Model registered:", model.name)

if __name__ == "__main__":
    main()