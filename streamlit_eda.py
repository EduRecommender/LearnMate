import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
import numpy as np
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import ast
import re
import time
from datetime import datetime

# Set page config
st.set_page_config(page_title="LearnMate Chat Analysis", page_icon="📊", layout="wide")

# Download NLTK resources if not already downloaded
@st.cache_resource
def download_nltk_resources():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        
download_nltk_resources()

# Initialize session state for tracking data refresh
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = datetime.now()

# Get base directory (works both locally and on Streamlit Cloud)
def get_base_dir():
    # If running on Streamlit Cloud
    if os.getenv('STREAMLIT_SHARING'):
        return os.path.dirname(os.path.abspath(__file__))
    
    # If running locally - use the path from your local setup
    local_path = "/home/sebas/Desktop/ie_dev/y3.2/reco/LearnMate"
    if os.path.exists(local_path):
        return local_path
    
    # Fallback to current directory
    return os.path.dirname(os.path.abspath(__file__))

# Load data with TTL cache for automatic refreshing (every 60 seconds)
@st.cache_data(ttl=60)
def load_data():
    base_dir = get_base_dir()
    processed_dir = os.path.join(base_dir, "backend/data/processed")
    
    # Check if processed files exist, otherwise process raw data
    chat_csv = os.path.join(processed_dir, "processed_chat_data.csv")
    metrics_csv = os.path.join(processed_dir, "processed_metrics_data.csv")
    
    if os.path.exists(chat_csv) and os.path.exists(metrics_csv):
        chat_df = pd.read_csv(chat_csv)
        metrics_df = pd.read_csv(metrics_csv)
        
        # Convert string representations of lists back to actual lists
        if 'topics' in chat_df.columns:
            chat_df['topics'] = chat_df['topics'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])
            
        # Convert datetime columns
        datetime_cols = [col for col in chat_df.columns if 'dt' in col or 'time' in col]
        for col in datetime_cols:
            if col in chat_df.columns:
                chat_df[col] = pd.to_datetime(chat_df[col], errors='coerce')
                
        if 'timestamp_dt' in metrics_df.columns:
            metrics_df['timestamp_dt'] = pd.to_datetime(metrics_df['timestamp_dt'], errors='coerce')
    else:
        # If processed files don't exist, run the processing script
        import subprocess
        script_path = os.path.join(base_dir, "data_processing.py")
        
        if os.path.exists(script_path):
            subprocess.run(["python", script_path])
            
            # Try loading again
            if os.path.exists(chat_csv) and os.path.exists(metrics_csv):
                chat_df = pd.read_csv(chat_csv)
                metrics_df = pd.read_csv(metrics_csv)
                
                # Convert string representations of lists back to actual lists
                if 'topics' in chat_df.columns:
                    chat_df['topics'] = chat_df['topics'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])
                
                # Convert datetime columns
                datetime_cols = [col for col in chat_df.columns if 'dt' in col or 'time' in col]
                for col in datetime_cols:
                    if col in chat_df.columns:
                        chat_df[col] = pd.to_datetime(chat_df[col], errors='coerce')
                        
                if 'timestamp_dt' in metrics_df.columns:
                    metrics_df['timestamp_dt'] = pd.to_datetime(metrics_df['timestamp_dt'], errors='coerce')
            else:
                st.error("Failed to process and load data. Please check the file paths.")
                return None, None
        else:
            st.error(f"Processing script not found at {script_path}")
            return None, None
    
    # Update last refresh time in session state
    st.session_state.last_refresh_time = datetime.now()
    
    return chat_df, metrics_df

# Function to force reprocess data from raw files
def reprocess_data():
    base_dir = get_base_dir()
    script_path = os.path.join(base_dir, "data_processing.py")
    
    if os.path.exists(script_path):
        with st.spinner("Reprocessing data from raw files..."):
            import subprocess
            subprocess.run(["python", script_path])
            # Clear the cache to force reload
            st.cache_data.clear()
            st.session_state.last_refresh_time = datetime.now()
            st.success("Data reprocessed successfully!")
            time.sleep(1)  # Small delay for UI feedback
            st.rerun()  # Rerun the app to show new data
    else:
        st.error(f"Processing script not found at {script_path}")

# Extract entities and relationships from responses
def extract_entities_from_response(text):
    if not isinstance(text, str) or not text:
        return []
    
    # Simple pattern matching for educational entities
    subjects = re.findall(r'\b(math|science|history|english|computer science|physics|chemistry|biology)\b', 
                         text.lower())
    resources = re.findall(r'\b(book|video|lecture|tutorial|exercise|problem|quiz|test|exam)\b', 
                          text.lower())
    timeframes = re.findall(r'\b(day|week|month|hour|minute|session)\b', text.lower())
    
    entities = list(set(subjects + resources + timeframes))
    return entities

# Analyze response sentiment and complexity
def analyze_response_characteristics(df):
    if 'response_content' not in df.columns:
        return df
    
    # Response complexity based on length and sentence structure
    df['response_word_count'] = df['response_content'].apply(
        lambda x: len(word_tokenize(x)) if isinstance(x, str) else 0
    )
    
    df['response_avg_word_length'] = df['response_content'].apply(
        lambda x: np.mean([len(word) for word in word_tokenize(x)]) if isinstance(x, str) and len(word_tokenize(x)) > 0 else 0
    )
    
    # Extract entities
    df['entities'] = df['response_content'].apply(extract_entities_from_response)
    
    return df

# Main app
def main():
    st.title("LearnMate Chat Response Analysis")
    st.markdown("""
    This dashboard provides insights into chat responses for improving chatbot and recommendation systems.
    """)
    
    # Add refresh controls at the top
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"Data last refreshed: {st.session_state.last_refresh_time.strftime('%Y-%m-%d %H:%M:%S')}")
        st.caption("Data automatically refreshes every 60 seconds")
    
    with col2:
        if st.button("🔄 Refresh Data Now"):
            st.cache_data.clear()
            st.success("Cache cleared! Loading fresh data...")
            time.sleep(1)  # Small delay for UI feedback
            st.rerun()  # Rerun the app to show new data
    
    with col3:
        if st.button("🔄 Reprocess All Data"):
            reprocess_data()
    
    # Load data
    chat_df, metrics_df = load_data()
    
    if chat_df is None or metrics_df is None:
        st.warning("Data could not be loaded. Please check the file paths.")
        return
    
    # Add real-time stats
    st.sidebar.title("Real-time Stats")
    
    if 'started_at_dt' in chat_df.columns:
        latest_request = chat_df['started_at_dt'].max()
        st.sidebar.metric("Latest Request", latest_request.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(latest_request) else "N/A")
    
    if 'request_id' in chat_df.columns:
        total_requests = len(chat_df)
        st.sidebar.metric("Total Requests", total_requests)
        
        # Get requests in the last 24 hours
        if 'started_at_dt' in chat_df.columns:
            now = pd.Timestamp.now()
            last_24h = now - pd.Timedelta(days=1)
            recent_requests = len(chat_df[chat_df['started_at_dt'] > last_24h])
            st.sidebar.metric("Requests (Last 24h)", recent_requests)
    
    # Add more analyses
    chat_df = analyze_response_characteristics(chat_df)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Overview", "Response Analysis", "Topics & Entities", "User Metrics", "Recommendation Insights"]
    )
    
    if page == "Overview":
        st.header("Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Chat Requests", len(chat_df))
            st.metric("Unique Users", len(chat_df['user_id'].unique()) if 'user_id' in chat_df.columns else "N/A")
            
        with col2:
            st.metric("Avg. Processing Time (s)", 
                      round(metrics_df['processing_time'].mean(), 2) if 'processing_time' in metrics_df.columns else "N/A")
            st.metric("Success Rate", 
                      f"{round(metrics_df['success'].mean() * 100, 1)}%" if 'success' in metrics_df.columns else "N/A")
        
        # Task type distribution
        if 'task_type' in metrics_df.columns:
            st.subheader("Task Type Distribution")
            task_counts = metrics_df['task_type'].value_counts().reset_index()
            task_counts.columns = ['Task Type', 'Count']
            
            fig = px.pie(task_counts, values='Count', names='Task Type', 
                        title='Distribution of Task Types',
                        color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig)
        
        # Response length distribution
        if 'response_length' in chat_df.columns:
            st.subheader("Response Length Distribution")
            
            fig = px.histogram(chat_df, x='response_length', 
                              title='Distribution of Response Lengths',
                              labels={'response_length': 'Response Length (characters)'},
                              nbins=20)
            st.plotly_chart(fig)
        
        # Processing time over time
        if 'timestamp_dt' in metrics_df.columns and 'processing_time' in metrics_df.columns:
            st.subheader("Processing Time Trend")
            
            # Resample by hour for better visualization
            metrics_df = metrics_df.sort_values('timestamp_dt')
            
            # Fix: Only include numeric columns when resampling or specify numeric_only=True
            # Create a new DataFrame with just timestamp and processing_time
            time_df = metrics_df[['timestamp_dt', 'processing_time']].copy()
            metrics_hourly = time_df.set_index('timestamp_dt').resample('h').mean().reset_index()
            
            fig = px.line(metrics_hourly, x='timestamp_dt', y='processing_time', 
                         title='Average Processing Time Over Time',
                         labels={'timestamp_dt': 'Time', 'processing_time': 'Avg. Processing Time (s)'})
            st.plotly_chart(fig)
    
    elif page == "Response Analysis":
        st.header("Response Analysis")
        
        # Response type distribution
        response_type_cols = [col for col in chat_df.columns if col.startswith('is_')]
        if response_type_cols:
            st.subheader("Response Type Distribution")
            
            response_types = pd.DataFrame({
                'Type': [col.replace('is_', '') for col in response_type_cols],
                'Count': [chat_df[col].sum() for col in response_type_cols]
            })
            
            fig = px.bar(response_types, x='Type', y='Count',
                        title='Distribution of Response Types',
                        color='Type',
                        color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig)
        
        # Word count distribution
        if 'response_word_count' in chat_df.columns:
            st.subheader("Response Complexity")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.histogram(chat_df, x='response_word_count',
                                  title='Distribution of Response Word Counts',
                                  labels={'response_word_count': 'Word Count'},
                                  nbins=20)
                st.plotly_chart(fig)
            
            with col2:
                if 'response_avg_word_length' in chat_df.columns:
                    fig = px.histogram(chat_df, x='response_avg_word_length',
                                     title='Distribution of Avg. Word Length',
                                     labels={'response_avg_word_length': 'Avg. Word Length'},
                                     nbins=20)
                    st.plotly_chart(fig)
        
        # Sample responses
        st.subheader("Sample Responses")
        if 'response_content' in chat_df.columns and not chat_df['response_content'].empty:
            # Get a few samples from different length categories
            if len(chat_df) > 5:
                short_sample = chat_df.nsmallest(1, 'response_length')['response_content'].iloc[0]
                medium_sample = chat_df.iloc[len(chat_df)//2]['response_content']
                long_sample = chat_df.nlargest(1, 'response_length')['response_content'].iloc[0]
                
                with st.expander("Short Response Example"):
                    st.write(short_sample)
                
                with st.expander("Medium Response Example"):
                    st.write(medium_sample)
                
                with st.expander("Long Response Example"):
                    st.write(long_sample)
            else:
                sample = chat_df['response_content'].iloc[0] if not chat_df['response_content'].empty else "No sample available"
                with st.expander("Response Example"):
                    st.write(sample)
    
    elif page == "Topics & Entities":
        st.header("Topics & Entities Analysis")
        
        # Get all topics and their frequencies
        if 'topics' in chat_df.columns:
            all_topics = [topic for sublist in chat_df['topics'].tolist() for topic in sublist]
            topic_counts = Counter(all_topics)
            
            if topic_counts:
                st.subheader("Most Common Topics")
                
                topic_df = pd.DataFrame({
                    'Topic': list(topic_counts.keys()),
                    'Frequency': list(topic_counts.values())
                }).sort_values('Frequency', ascending=False).head(20)
                
                fig = px.bar(topic_df, x='Topic', y='Frequency',
                            title='Top 20 Topics in Responses',
                            color='Frequency',
                            color_continuous_scale='Viridis')
                st.plotly_chart(fig)
                
                # Word cloud of topics
                st.subheader("Topic Word Cloud")
                
                wordcloud = WordCloud(
                    width=800, height=400,
                    background_color='white',
                    colormap='viridis',
                    max_words=100
                ).generate_from_frequencies(topic_counts)
                
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
        
        # Entity analysis
        if 'entities' in chat_df.columns:
            all_entities = [entity for sublist in chat_df['entities'].tolist() for entity in sublist]
            entity_counts = Counter(all_entities)
            
            if entity_counts:
                st.subheader("Educational Entities Mentioned")
                
                entity_df = pd.DataFrame({
                    'Entity': list(entity_counts.keys()),
                    'Frequency': list(entity_counts.values())
                }).sort_values('Frequency', ascending=False)
                
                fig = px.bar(entity_df, x='Entity', y='Frequency',
                            title='Educational Entities in Responses',
                            color='Frequency',
                            color_continuous_scale='Plasma')
                st.plotly_chart(fig)
                
                # Entity co-occurrence analysis
                st.subheader("Entity Co-occurrence")
                
                # Create co-occurrence matrix
                entities = list(entity_counts.keys())
                co_occur = np.zeros((len(entities), len(entities)))
                
                for idx, row in chat_df.iterrows():
                    row_entities = row['entities']
                    for i, e1 in enumerate(entities):
                        for j, e2 in enumerate(entities):
                            if e1 in row_entities and e2 in row_entities and i != j:
                                co_occur[i, j] += 1
                
                # Plot heatmap for top entities
                top_entities = entity_df.head(10)['Entity'].tolist()
                top_indices = [entities.index(e) for e in top_entities]
                
                if len(top_indices) > 1:  # Need at least 2 entities for co-occurrence
                    top_co_occur = co_occur[np.ix_(top_indices, top_indices)]
                    
                    fig = px.imshow(top_co_occur,
                                  x=top_entities,
                                  y=top_entities,
                                  color_continuous_scale='Viridis',
                                  title='Entity Co-occurrence Heatmap')
                    st.plotly_chart(fig)
    
    elif page == "User Metrics":
        st.header("User Interaction Metrics")
        
        if 'user_id' in chat_df.columns:
            user_counts = chat_df['user_id'].value_counts().reset_index()
            user_counts.columns = ['User ID', 'Request Count']
            
            st.subheader("Requests per User")
            fig = px.bar(user_counts, x='User ID', y='Request Count',
                        title='Number of Requests per User',
                        color='Request Count',
                        color_continuous_scale='Viridis')
            st.plotly_chart(fig)
        
        # Session analysis
        if 'session_id' in chat_df.columns:
            session_counts = chat_df['session_id'].value_counts().reset_index()
            session_counts.columns = ['Session ID', 'Request Count']
            
            st.subheader("Requests per Session")
            fig = px.bar(session_counts, x='Session ID', y='Request Count',
                        title='Number of Requests per Session',
                        color='Request Count',
                        color_continuous_scale='Viridis')
            st.plotly_chart(fig)
            
            # Time between requests in a session
            if 'started_at_dt' in chat_df.columns:
                st.subheader("Session Duration Analysis")
                
                session_durations = {}
                for session in chat_df['session_id'].unique():
                    session_data = chat_df[chat_df['session_id'] == session].sort_values('started_at_dt')
                    
                    if len(session_data) > 1:
                        first_time = session_data['started_at_dt'].iloc[0]
                        last_time = session_data['started_at_dt'].iloc[-1]
                        duration = (last_time - first_time).total_seconds() / 60  # in minutes
                        session_durations[session] = duration
                
                if session_durations:
                    duration_df = pd.DataFrame({
                        'Session ID': list(session_durations.keys()),
                        'Duration (minutes)': list(session_durations.values())
                    })
                    
                    fig = px.bar(duration_df, x='Session ID', y='Duration (minutes)',
                                title='Session Durations',
                                color='Duration (minutes)',
                                color_continuous_scale='Viridis')
                    st.plotly_chart(fig)
        
        # User behavior analysis
        if 'message' in chat_df.columns and 'user_id' in chat_df.columns:
            st.subheader("User Query Length Analysis")
            
            chat_df['query_length'] = chat_df['message'].apply(
                lambda x: len(x) if isinstance(x, str) else 0
            )
            
            # Plot average query length by user
            user_query_length = chat_df.groupby('user_id')['query_length'].mean().reset_index()
            user_query_length.columns = ['User ID', 'Avg Query Length']
            
            fig = px.bar(user_query_length, x='User ID', y='Avg Query Length',
                        title='Average Query Length by User',
                        color='Avg Query Length',
                        color_continuous_scale='Viridis')
            st.plotly_chart(fig)
    
    elif page == "Recommendation Insights":
        st.header("Recommendation System Insights")
        
        # Analysis specifically for recommendation system improvements
        st.subheader("Key Insights for Recommendation System")
        
        # Topic-based recommendation analysis
        if 'topics' in chat_df.columns and 'user_id' in chat_df.columns:
            st.write("### User-Topic Affinity Analysis")
            
            # Create user-topic matrix
            user_topics = {}
            
            for idx, row in chat_df.iterrows():
                user_id = row['user_id']
                topics = row['topics']
                
                if user_id not in user_topics:
                    user_topics[user_id] = Counter()
                
                user_topics[user_id].update(topics)
            
            # Get top topics for each user
            user_top_topics = {}
            for user, topics_counter in user_topics.items():
                user_top_topics[user] = [topic for topic, _ in topics_counter.most_common(5)]
            
            for user, top_topics in user_top_topics.items():
                st.write(f"**User {user} Top Topics:**")
                for i, topic in enumerate(top_topics, 1):
                    st.write(f"{i}. {topic}")
                st.write("---")
        
        # Response type preference by user
        response_type_cols = [col for col in chat_df.columns if col.startswith('is_')]
        if response_type_cols and 'user_id' in chat_df.columns:
            st.write("### User Response Type Preferences")
            
            # Calculate percentage of each response type by user
            user_response_prefs = {}
            
            for user in chat_df['user_id'].unique():
                user_data = chat_df[chat_df['user_id'] == user]
                prefs = {}
                
                for col in response_type_cols:
                    response_type = col.replace('is_', '')
                    prefs[response_type] = user_data[col].mean() * 100
                
                user_response_prefs[user] = prefs
            
            # Create visualization
            user_pref_data = []
            for user, prefs in user_response_prefs.items():
                for response_type, percentage in prefs.items():
                    user_pref_data.append({
                        'User ID': user,
                        'Response Type': response_type,
                        'Percentage': percentage
                    })
            
            user_pref_df = pd.DataFrame(user_pref_data)
            
            fig = px.bar(user_pref_df, x='User ID', y='Percentage', color='Response Type',
                        title='Response Type Preferences by User',
                        labels={'Percentage': 'Percentage of Responses (%)'},
                        barmode='group')
            st.plotly_chart(fig)
        
        # Recommendation for system improvements
        st.subheader("System Improvement Recommendations")
        
        st.write("""
        Based on the data analysis, here are key recommendations for improving the recommendation system:
        
        1. **Personalized Content**: Leverage user-topic affinity to create personalized content recommendations
        2. **Response Format Optimization**: Adapt response formats based on user preferences
        3. **Educational Resource Suggestions**: Recommend specific educational resources mentioned in successful responses
        4. **Session-Aware Recommendations**: Use session duration and patterns to improve recommendation timing
        5. **Complexity Adaptation**: Adjust response complexity based on user query patterns
        """)

    # Footer with auto-refresh information
    st.sidebar.markdown("---")
    st.sidebar.caption("Data automatically refreshes every 60 seconds")

    # Show deployment info
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Deployment Info")
    st.sidebar.markdown(f"Running in: **{'Streamlit Cloud' if os.getenv('STREAMLIT_SHARING') else 'Local Environment'}**")
    st.sidebar.markdown(f"Last update: {datetime.now().strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main() 