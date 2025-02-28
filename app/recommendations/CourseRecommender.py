import os
from recommendations.base import BaseRecommender
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from sklearn.metrics import ndcg_score
from sklearn.feature_extraction.text import CountVectorizer
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re

class CourseRecommender2(BaseRecommender):
    def __init__(self):
        super().__init__("course_recommender")
        self.vectorizer = None
        self.tfidf_matrix = None
        self.cosine_sim = None
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()

    def load_data(self):
        """
        Load and preprocess the training data.
        """
        # Load the training data (e.g., course descriptions)
        data_path = os.path.join("input_data", "kaggle_filtered_courses.csv")
        self.data = pd.read_csv(data_path)
        
        # Preprocess the data (e.g., normalize text, combine features)
        self.data['Course Description'] = self.data['Course Description'].str.lower()
        self.data['About'] = self.data['About'].str.lower()
        # Ensure 'Difficulty Level' column exists and is of string type
        if 'Difficulty Level' not in self.data.columns:
            self.data['Difficulty Level'] = 'Unknown'  # Or some other default value
        self.data['Difficulty Level'] = self.data['Difficulty Level'].astype(str).str.lower()
        self.data['combined_features'] = (
            self.data['Name'] + ' ' + self.data['About'] + ' ' + self.data['Course Description'] + ' ' + self.data['Difficulty Level']
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

    def preprocess_text(self, text):
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join([word for word in text.split() if word not in self.stop_words])
        text = ' '.join([self.lemmatizer.lemmatize(word) for word in text.split()])
        return text

    def train(self):
        """
        Train the TF-IDF vectorizer and compute the cosine similarity matrix.
        """
        self.data['combined_features'] = self.data['combined_features'].apply(self.preprocess_text)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=5) # Use n-grams
        self.tfidf_matrix = self.vectorizer.fit_transform(self.data['combined_features'])
        self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
        self.is_trained = True

    def predict(self, user_input, top_k=5, print_output=True):
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
        user_input = self.preprocess_text(user_input)
        
        # Vectorize the user input
        user_tfidf = self.vectorizer.transform([user_input])
        
        # Compute cosine similarity between user input and existing courses
        user_cosine_sim = cosine_similarity(user_tfidf, self.tfidf_matrix)
        
        # Get the indices of the top-k most similar courses
        similar_indices = user_cosine_sim[0].argsort()[-top_k:][::-1]
        
        # Return the recommended courses
        recommendations =  self.data.iloc[similar_indices].copy() # Use .copy() to avoid SettingWithCopyWarning
        recommendations['Category'] = recommendations['Category'].astype(str)
        
        if print_output:
            print(recommendations[['Name', 'University', 'Link', 'Category', 'Difficulty Level']])
        
        return recommendations