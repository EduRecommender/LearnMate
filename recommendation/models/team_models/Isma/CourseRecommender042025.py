#!/usr/bin/env python3
import os
import json
import logging
import re
import pandas as pd
import numpy as np
from itertools import islice
from recommendation.models.base import BaseRecommender
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from scipy.spatial.distance import jensenshannon
from scipy.special import kl_div
from sklearn.metrics import ndcg_score
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from tabulate import tabulate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class HybridRecommender(BaseRecommender):
    """
    A hybrid recommender that combines course, video, and book data with multiple similarity metrics.
    """
    def __init__(self, similarity_method="cosine"):
        super().__init__("hybrid_recommender")
        self.vectorizer = None
        self.tfidf_matrix = None
        self.similarity_matrix = None
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.courses_data = None
        self.videos_data = None
        self.books_data = None
        self.data = None
        self.similarity_method = similarity_method
        valid_methods = ["cosine", "kl_divergence", "jensen_shannon", "euclidean", "ensemble"]
        if similarity_method not in valid_methods:
            logging.warning(f"Invalid similarity method '{similarity_method}'. Using 'cosine' instead.")
            self.similarity_method = "cosine"
        self.is_trained = False

    def load_data(self):
        """
        Load and preprocess course, video, and book data.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))

        # Courses
        courses_path = os.path.join(project_root, "input_data", "kaggle_filtered_courses.csv")
        self.courses_data = pd.read_csv(courses_path)
        self.courses_data['Source'] = 'Course'
        self.courses_data['Course Description'] = self.courses_data['Course Description'].fillna('').str.lower()
        self.courses_data['About'] = self.courses_data['About'].fillna('').str.lower()
        if 'Difficulty Level' not in self.courses_data.columns:
            self.courses_data['Difficulty Level'] = 'Unknown'
        self.courses_data['Difficulty Level'] = self.courses_data['Difficulty Level'].astype(str).str.lower()
        self.courses_data['combined_features'] = (
            self.courses_data['Name'] + ' ' +
            self.courses_data['About'] + ' ' +
            self.courses_data['Course Description'] + ' ' +
            self.courses_data['Difficulty Level']
        )
        course_columns = ['Name', 'University', 'Link', 'Category', 'Difficulty Level', 'combined_features', 'Source']
        self.courses_data = self.courses_data[course_columns].copy()

        # Videos
        videos_path = os.path.join(project_root, "input_data", "youtube_videos.csv")
        try:
            self.videos_data = pd.read_csv(videos_path)
            self.videos_data['Source'] = 'YouTube'
            self.videos_data['Description'] = self.videos_data['description'].fillna('').str.lower()
            self.videos_data['Transcript'] = self.videos_data['transcript'].fillna('').str.lower()
            self.videos_data['About'] = self.videos_data['title'].fillna('').str.lower()
            self.videos_data['Name'] = self.videos_data['title']
            self.videos_data['University'] = self.videos_data['channel']
            self.videos_data['Link'] = self.videos_data['url']
            self.videos_data['Category'] = 'Video'
            self.videos_data['Difficulty Level'] = 'Unknown'
            self.videos_data['combined_features'] = (
                self.videos_data['Name'] + ' ' +
                self.videos_data['About'] + ' ' +
                self.videos_data['Description'] + ' ' +
                self.videos_data['Transcript']
            )
            video_columns = ['Name', 'University', 'Link', 'Category', 'Difficulty Level', 'combined_features', 'Source']
            self.videos_data = self.videos_data[video_columns].copy()
        except Exception as e:
            logging.warning(f"Could not load YouTube data: {e}")
            self.videos_data = pd.DataFrame(columns=course_columns)

        # Books
        books_path = os.path.join(project_root, "input_data", "books.csv")
        try:
            self.books_data = pd.read_csv(books_path)
            self.books_data['Source'] = 'Book'
            # Use CSV 'Category' if present, else default to 'Book'
            if 'Category' in self.books_data.columns:
                self.books_data['Category'] = self.books_data['Category'].fillna('Book')
            else:
                self.books_data['Category'] = 'Book'
            # Map title/publisher
            self.books_data['Name'] = self.books_data['title'].fillna('').str.lower()
            self.books_data['Publisher'] = self.books_data['publisher'].fillna('').str.lower()
            self.books_data['Synopsis'] = self.books_data['synopsis'].fillna('').str.lower()
            self.books_data['Link'] = ''
            self.books_data['Difficulty Level'] = 'Unknown'
            # Combine features
            synopsis = self.books_data.get('synopsis', pd.Series()).fillna('').str.lower()
            subjects = self.books_data.get('subjects', pd.Series()).fillna('').apply(
                lambda x: ' '.join(json.loads(x)) if isinstance(x, str) else ''
            )
            self.books_data['combined_features'] = (
                self.books_data['Name'] + ' ' + synopsis + ' ' + subjects
            )
            book_columns = ['Name', 'University', 'Link', 'Category', 'Difficulty Level', 'combined_features', 'Source']
            self.books_data = self.books_data[book_columns].copy()
        except Exception as e:
            logging.warning(f"Could not load Books data: {e}")
            self.books_data = pd.DataFrame(columns=course_columns)

        # Combine all data
        self.data = pd.concat([self.courses_data, self.videos_data, self.books_data], ignore_index=True)
        self.data['combined_features'] = self.data['combined_features'].apply(self.preprocess_text)

    def load_test_data(self):
        self.test_data = pd.DataFrame({
            'query': [
                "I want to learn programming basics",
                "I want to learn computer vision",
                "I want to learn data science",
                "Show me beginner courses on python",
                "I need advanced materials on machine learning"
            ],
            'ground_truth': [
                [1, 62, 137],
                [382, 306],
                [309, 273],
                [2, 62],
                [309, 382]
            ]
        })

    def preprocess_text(self, text):
        if not isinstance(text, str):
            return ""
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join([w for w in text.split() if w not in self.stop_words])
        text = ' '.join([self.lemmatizer.lemmatize(w) for w in text.split()])
        return text

    def train(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.9)
        self.tfidf_matrix = self.vectorizer.fit_transform(self.data['combined_features'])
        if self.similarity_method == "cosine":
            self.similarity_matrix = cosine_similarity(self.tfidf_matrix)
        elif self.similarity_method == "euclidean":
            d = euclidean_distances(self.tfidf_matrix)
            self.similarity_matrix = 1 / (1 + d)
        elif self.similarity_method == "kl_divergence":
            arr = np.maximum(self.tfidf_matrix.toarray(), 1e-10)
            norm = arr / arr.sum(axis=1, keepdims=True)
            n = norm.shape[0]
            mat = np.zeros((n,n))
            for i in range(n):
                for j in range(n):
                    mat[i,j] = (np.sum(kl_div(norm[i], norm[j])) + np.sum(kl_div(norm[j], norm[i]))) / 2
            self.similarity_matrix = 1 / (1 + mat)
        elif self.similarity_method == "jensen_shannon":
            arr = np.maximum(self.tfidf_matrix.toarray(), 1e-10)
            norm = arr / arr.sum(axis=1, keepdims=True)
            n = norm.shape[0]
            mat = np.zeros((n,n))
            for i in range(n):
                for j in range(n):
                    mat[i,j] = jensenshannon(norm[i], norm[j])
            self.similarity_matrix = 1 - mat
        else:
            cos = cosine_similarity(self.tfidf_matrix)
            d = euclidean_distances(self.tfidf_matrix)
            eu = 1 / (1 + d)
            self.similarity_matrix = 0.7 * cos + 0.3 * eu
        self.is_trained = True

    def predict(self, user_input, top_k=5, difficulty_level=None, print_output=True):
        inp = self.preprocess_text(user_input.lower())
        vec = self.vectorizer.transform([inp])
        if self.similarity_method == "cosine":
            scores = cosine_similarity(vec, self.tfidf_matrix)[0]
        elif self.similarity_method == "euclidean":
            d = euclidean_distances(vec, self.tfidf_matrix)[0]
            scores = 1 / (1 + d)
        else:
            scores = cosine_similarity(vec, self.tfidf_matrix)[0]
        results = self.data.copy()
        results['similarity_score'] = scores
        if difficulty_level:
            results = results[results['Difficulty Level'].str.lower() == difficulty_level.lower()]
        recs = results.sort_values('similarity_score', ascending=False).head(top_k)
        if print_output:
            df = recs[['Name','University','Link','Category','Difficulty Level','Source']].copy()
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
            print(f"Similarity: {self.similarity_method}")
        return recs

    def evaluate(self, top_k=10):
        precision, recall, ndcg = [], [], []
        for _, row in self.test_data.iterrows():
            recs = self.predict(row['query'], top_k, print_output=False)
            idx = recs.index.tolist()
            gt = set(row['ground_truth'])
            p = len(gt & set(idx)) / top_k
            r = len(gt & set(idx)) / len(gt) if gt else 0
            rel = [1 if i in gt else 0 for i in idx]
            nd = ndcg_score([rel], [rel], k=top_k) if any(rel) else 0
            precision.append(p)
            recall.append(r)
            ndcg.append(nd)
        return {
            'precisionk': np.mean(precision),
            'recallk': np.mean(recall),
            'ndcgk': np.mean(ndcg),
            'similarity_method': self.similarity_method
        }
