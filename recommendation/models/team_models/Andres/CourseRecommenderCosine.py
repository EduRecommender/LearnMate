import os
from recommendation.models.base import BaseRecommender
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from sklearn.metrics import ndcg_score

class CourseRecommenderCosine(BaseRecommender):
    def __init__(self):
        super().__init__("course_recommender")
        self.vectorizer = None
        self.tfidf_matrix = None
        self.cosine_sim = None

    def load_data(self):
        """
        Load and preprocess the training data.

        """
        # Load the training data (e.g., course descriptions)
        data_path = os.path.join("raw_data", "EdX.csv")
        self.data = pd.read_csv(data_path)
        
        # Preprocess the data (e.g., normalize text, combine features)
        self.data['Course Description'] = self.data['Course Description'].str.lower()
        self.data['About'] = self.data['About'].str.lower()
        self.data['combined_features'] = (
            self.data['Name'] + ' ' + self.data['About'] + ' ' + self.data['Course Description']
        )

    def load_test_data(self):
        """
        Load and preprocess the test data.
        These are just some random samples to use as an example so the results shouldn't be taken seriously.
        """
        # Define test queries and ground truth
        self.test_data = pd.DataFrame({
            'query': [
                "I want to learn programming basics",
                "I want to learn computer vision",
                "I want to learn data science"
            ],
            # Random indices of relevant courses for each query to use as sample training data
            'ground_truth': [
                [1, 62, 137], 
                [382, 306],
                [309, 273]     
            ]
        })

    def evaluate(self, top_k=5):
        """
        Evaluate the model using its own test data.
        """
        precision_scores = []
        recall_scores = []
        ndcg_scores = []
        
        for _, row in self.test_data.iterrows():
            query = row['query']
            ground_truth = row['ground_truth']
            
            # Get recommendations
            recommendations = self.predict(query, top_k)
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
    
    def train(self):
        """
        Train the TF-IDF vectorizer and compute the cosine similarity matrix.
        """
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(self.data['combined_features'])
        self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
        self.is_trained = True

    def predict(self, user_input, top_k=5):
        """
        Recommend courses based on user input.
        
        Args:
            user_input (str): The user's input query.
            top_k (int): Number of recommendations to return.
        
        Returns:
            pd.DataFrame: A DataFrame containing the recommended courses.
        """
        # Normalize the user input
        user_input = user_input.lower()
        
        # Vectorize the user input
        user_tfidf = self.vectorizer.transform([user_input])
        
        # Compute cosine similarity between user input and existing courses
        user_cosine_sim = cosine_similarity(user_tfidf, self.tfidf_matrix)
        
        # Get the indices of the top-k most similar courses
        similar_indices = user_cosine_sim[0].argsort()[-top_k:][::-1]
        
        # Return the recommended courses
        return self.data.iloc[similar_indices]