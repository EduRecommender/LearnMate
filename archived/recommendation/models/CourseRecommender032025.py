import os
from recommendation.models.base import BaseRecommender
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from scipy.spatial.distance import jensenshannon
from scipy.special import kl_div
import pandas as pd
import numpy as np
from sklearn.metrics import ndcg_score
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
import logging

class HybridRecommender(BaseRecommender):
    """
    A hybrid recommender that combines course and video data with multiple similarity metrics.
    
    This recommender:
    1. Uses data from both Kaggle courses and YouTube videos
    2. Implements multiple similarity metrics (cosine, KL divergence, Jensen-Shannon)
    3. Considers difficulty level in recommendations
    4. Applies text preprocessing with NLP techniques
    """
    
    def __init__(self, similarity_method="cosine"):
        """
        Initialize the hybrid recommender.
        
        Args:
            similarity_method (str): Method to use for similarity calculation.
                Options: "cosine", "kl_divergence", "jensen_shannon", "euclidean", "ensemble"
        """
        super().__init__("hybrid_recommender")
        self.vectorizer = None
        self.tfidf_matrix = None
        self.similarity_matrix = None
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.courses_data = None
        self.videos_data = None
        self.data = None
        self.similarity_method = similarity_method
        
        # Validate similarity method
        valid_methods = ["cosine", "kl_divergence", "jensen_shannon", "euclidean", "ensemble"]
        if similarity_method not in valid_methods:
            logging.warning(f"Invalid similarity method '{similarity_method}'. Using 'cosine' instead.")
            self.similarity_method = "cosine"

    def load_data(self):
        """
            Load and preprocess both course and video data.
        """
        # Get the project root directory (LearnMate)
        # The path needs to go up 4 levels from the file location, not 5
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
    
        # Load the course data with absolute path
        courses_path = os.path.join(project_root, "data/input_data", "kaggle_filtered_courses.csv")
        print(f"Loading courses from: {courses_path}")
        self.courses_data = pd.read_csv(courses_path)
    
        # Load the YouTube videos data if available
        videos_path = os.path.join(project_root, "data/input_data", "youtube_videos.csv")
        print(f"Loading videos from: {videos_path}")
        
        try:
            self.videos_data = pd.read_csv(videos_path)
            # Add a source column to distinguish between courses and videos
            self.videos_data['Source'] = 'YouTube'
            self.courses_data['Source'] = 'Course'
            
            # Process video data
            self.videos_data['Description'] = self.videos_data['description'].fillna('').str.lower()
            self.videos_data['Transcript'] = self.videos_data['transcript'].fillna('').str.lower()
            self.videos_data['About'] = self.videos_data['title'].fillna('').str.lower()
            self.videos_data['Name'] = self.videos_data['title']
            self.videos_data['University'] = self.videos_data['channel']
            self.videos_data['Link'] = self.videos_data['url']
            self.videos_data['Category'] = 'Video'
            self.videos_data['Difficulty Level'] = 'Unknown'  # Default difficulty for videos
            
            # Create combined features for videos
            self.videos_data['combined_features'] = (
                self.videos_data['Name'] + ' ' + 
                self.videos_data['About'] + ' ' + 
                self.videos_data['Description'] + ' ' + 
                self.videos_data['Transcript']
            )
            
            # Select relevant columns for videos
            video_columns = ['Name', 'University', 'Link', 'Category', 'Difficulty Level', 
                           'combined_features', 'Source']
            self.videos_data = self.videos_data[video_columns].copy()
            
        except Exception as e:
            logging.warning(f"Could not load YouTube videos data: {e}")
            self.videos_data = pd.DataFrame(columns=['Name', 'University', 'Link', 'Category', 
                                                   'Difficulty Level', 'combined_features', 'Source'])
        
        # Preprocess the course data
        self.courses_data['Course Description'] = self.courses_data['Course Description'].fillna('').str.lower()
        self.courses_data['About'] = self.courses_data['About'].fillna('').str.lower()
        
        # Ensure 'Difficulty Level' column exists and is of string type
        if 'Difficulty Level' not in self.courses_data.columns:
            self.courses_data['Difficulty Level'] = 'Unknown'
        self.courses_data['Difficulty Level'] = self.courses_data['Difficulty Level'].astype(str).str.lower()
        
        # Create combined features for courses
        self.courses_data['combined_features'] = (
            self.courses_data['Name'] + ' ' + 
            self.courses_data['About'] + ' ' + 
            self.courses_data['Course Description'] + ' ' + 
            self.courses_data['Difficulty Level']
        )
        
        # Select relevant columns for courses
        course_columns = ['Name', 'University', 'Link', 'Category', 'Difficulty Level', 
                        'combined_features', 'Source']
        self.courses_data = self.courses_data[course_columns].copy()
        
        # Combine datasets
        self.data = pd.concat([self.courses_data, self.videos_data], ignore_index=True)
        
        # Apply text preprocessing
        self.data['combined_features'] = self.data['combined_features'].apply(self.preprocess_text)

    def load_test_data(self):
        """
        Load and preprocess the test data.
        """
        # Define test queries and ground truth
        self.test_data = pd.DataFrame({
            'query': [
                "I want to learn programming basics",
                "I want to learn computer vision",
                "I want to learn data science",
                "Show me beginner courses on python",
                "I need advanced materials on machine learning"
            ],
            # Random indices of relevant content for each query
            'ground_truth': [
                [1, 62, 137], 
                [382, 306],
                [309, 273],
                [2, 62],
                [309, 382]
            ]
        })

    def preprocess_text(self, text):
        """
        Preprocess text by removing punctuation, stopwords, and lemmatizing.
        
        Args:
            text (str): The text to preprocess.
            
        Returns:
            str: The preprocessed text.
        """
        if not isinstance(text, str):
            return ""
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove stopwords
        text = ' '.join([word for word in text.split() if word not in self.stop_words])
        
        # Lemmatize
        text = ' '.join([self.lemmatizer.lemmatize(word) for word in text.split()])
        
        return text

    def train(self):
        """
        Train the TF-IDF vectorizer and compute the similarity matrix.
        """
        # Initialize and fit the TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9)
        self.tfidf_matrix = self.vectorizer.fit_transform(self.data['combined_features'])
        
        # Compute similarity matrix based on selected method
        if self.similarity_method == "cosine":
            self.similarity_matrix = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
        elif self.similarity_method == "euclidean":
            # Convert to similarity (inverse of distance)
            distances = euclidean_distances(self.tfidf_matrix, self.tfidf_matrix)
            self.similarity_matrix = 1 / (1 + distances)  # Convert to similarity
        elif self.similarity_method == "kl_divergence":
            # Normalize TF-IDF to probability-like values
            tfidf_array = self.tfidf_matrix.toarray()
            tfidf_array = np.maximum(tfidf_array, 1e-10)  # Avoid zeros
            row_sums = tfidf_array.sum(axis=1)
            normalized_tfidf = tfidf_array / row_sums[:, np.newaxis]
            
            # Calculate KL divergence for each pair
            n_samples = normalized_tfidf.shape[0]
            kl_matrix = np.zeros((n_samples, n_samples))
            
            for i in range(n_samples):
                for j in range(n_samples):
                    # Symmetric KL divergence
                    kl_ij = np.sum(kl_div(normalized_tfidf[i], normalized_tfidf[j]))
                    kl_ji = np.sum(kl_div(normalized_tfidf[j], normalized_tfidf[i]))
                    kl_matrix[i, j] = (kl_ij + kl_ji) / 2
            
            # Convert to similarity (inverse of divergence)
            self.similarity_matrix = 1 / (1 + kl_matrix)
        
        elif self.similarity_method == "jensen_shannon":
            # Normalize TF-IDF to probability-like values
            tfidf_array = self.tfidf_matrix.toarray()
            tfidf_array = np.maximum(tfidf_array, 1e-10)  # Avoid zeros
            row_sums = tfidf_array.sum(axis=1)
            normalized_tfidf = tfidf_array / row_sums[:, np.newaxis]
            
            # Calculate Jensen-Shannon distance for each pair
            n_samples = normalized_tfidf.shape[0]
            js_matrix = np.zeros((n_samples, n_samples))
            
            for i in range(n_samples):
                for j in range(n_samples):
                    js_matrix[i, j] = jensenshannon(normalized_tfidf[i], normalized_tfidf[j])
            
            # Convert to similarity (inverse of distance)
            self.similarity_matrix = 1 - js_matrix  # JS is already normalized
            
        elif self.similarity_method == "ensemble":
            # Compute multiple similarity matrices and combine them
            cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
            
            # Euclidean distance-based similarity
            euclidean_dist = euclidean_distances(self.tfidf_matrix, self.tfidf_matrix)
            euclidean_sim = 1 / (1 + euclidean_dist)
            
            # Take weighted average (0.7 * cosine + 0.3 * euclidean)
            self.similarity_matrix = 0.7 * cosine_sim + 0.3 * euclidean_sim
        
        self.is_trained = True

    # In the predict method of HybridRecommender class

    def predict(self, user_input, top_k=5, difficulty_level=None, print_output=True):
        """
        Recommend content based on user input and optional difficulty level.

        Args:
            user_input (str): The user's input query.
            top_k (int): Number of recommendations to return.
            difficulty_level (str, optional): Filter by difficulty level.
            print_output (bool): Whether to print the recommendations.
    
        Returns:
            pd.DataFrame: A DataFrame containing the recommended content.
        """
        # Normalize and preprocess the user input
        user_input = user_input.lower()
        user_input = self.preprocess_text(user_input)

        # Vectorize the user input
        user_tfidf = self.vectorizer.transform([user_input])

        # Compute similarity between user input and existing content
        if self.similarity_method == "cosine":
            user_similarity = cosine_similarity(user_tfidf, self.tfidf_matrix)[0]
        elif self.similarity_method == "euclidean":
            distances = euclidean_distances(user_tfidf, self.tfidf_matrix)[0]
            user_similarity = 1 / (1 + distances)
        elif self.similarity_method in ["kl_divergence", "jensen_shannon", "ensemble"]:
            # For these methods, use the precomputed similarity matrix with the cosine similarity
            # between the user query and the content
            user_similarity = cosine_similarity(user_tfidf, self.tfidf_matrix)[0]

        # Create a copy of the data with similarity scores
        results = self.data.copy()
        results['similarity_score'] = user_similarity

        # Filter by difficulty level if specified
        if difficulty_level is not None:
            difficulty_level = difficulty_level.lower()
            results = results[results['Difficulty Level'].str.lower() == difficulty_level]

        # Sort by similarity score and get top-k results
        recommendations = results.sort_values('similarity_score', ascending=False).head(top_k)

        # Ensure all string columns are properly formatted
        for col in ['Name', 'University', 'Category', 'Difficulty Level', 'Source']:
            if col in recommendations.columns:
                recommendations[col] = recommendations[col].astype(str)

        if print_output:
            print("\n--- Recommended Content ---")
        
            # Select the columns to display
            display_cols = ['Name', 'University', 'Link', 'Category', 'Difficulty Level', 'Source']
            display_df = recommendations[display_cols].copy()
        
            # Truncate long strings for better display
            for col in display_df.columns:
                if col == 'Link':
                    # Shorten links for better display
                    display_df[col] = display_df[col].apply(lambda x: x[:60] + '...' if len(x) > 60 else x)
                elif col in ['Name', 'University']:
                    # Truncate long names
                    display_df[col] = display_df[col].apply(lambda x: x[:40] + '...' if len(x) > 40 else x)
        
            # Use tabulate to get a nicely formatted table
            from tabulate import tabulate
            print(tabulate(display_df, headers='keys', tablefmt='grid', showindex=False))
        
            print(f"\nSimilarity method: {self.similarity_method}")

        return recommendations

    def evaluate(self, top_k=5):
        """
        Evaluate the model using its own test data.
        
        Args:
            top_k (int): Number of recommendations to consider for evaluation.
            
        Returns:
            dict: A dictionary containing evaluation metrics.
        """
        precision_scores = []
        recall_scores = []
        ndcg_scores = []
        
        for _, row in self.test_data.iterrows():
            query = row['query']
            ground_truth = row['ground_truth']
            
            # Get recommendations
            recommendations = self.predict(query, top_k, print_output=False)
            recommended_indices = recommendations.index.tolist()
            
            # Compute precision@k and recall@k
            relevant = set(ground_truth)
            retrieved = set(recommended_indices)
            precision = len(relevant.intersection(retrieved)) / top_k
            recall = len(relevant.intersection(retrieved)) / len(relevant) if len(relevant) > 0 else 0
            
            # Compute NDCG@k
            relevance_scores = [1 if idx in ground_truth else 0 for idx in recommended_indices]
            if any(relevance_scores):  # Check if there are any relevant items
                ndcg = ndcg_score([relevance_scores], [relevance_scores], k=top_k)
            else:
                ndcg = 0
            
            precision_scores.append(precision)
            recall_scores.append(recall)
            ndcg_scores.append(ndcg)
        
        return {
            'precisionk': np.mean(precision_scores),
            'recallk': np.mean(recall_scores),
            'ndcgk': np.mean(ndcg_scores),
            'similarity_method': self.similarity_method
        }