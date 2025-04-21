# LearnMate

### Web App Links:
- Recommendation System: [Link](https://learnmate.streamlit.app/)
- EDA + Data Vizualization for Data Scientists: [Link](https://learnmate-eda.streamlit.app)

### Branches:
- **main**: Main development branch
- **streamlit-eda**: Branch for Streamlit EDA dashboard and data processing pipeline

### Run:
```
pip install -r requirements.txt
```

### Run on Streamlit 
```
streamlit run home.py
```

## **AI-Powered Learning Assistant**

### **Team Name:** LearnMate
### **Team Members:** 
- Sebastian Perilla
- Ismael Picazo
- Farah Orfaly
- Daniel Mora
- Riley Martin
- Noah Schiek

---

## **Problem Statement**

Students often face difficulties finding reliable and personalized educational resources amidst the overwhelming amount of available content. Without effective guidance, many learners waste time navigating irrelevant or low-quality materials, which hampers their learning progress and motivation.

---

## **Proposed Solution**

LearnMate is an AI-powered solution that integrates:
1. **Chatbot**: A conversational interface for students to specify topics, preferences, and learning goals.
2. **Recommendation Engine**: A machine learning system offering personalized and curated educational resources, including books, videos, articles, and online courses.

LearnMate simplifies access to quality resources, enabling students to focus on learning rather than searching.

---

## **Features**

### **Chatbot:**
- User-friendly interface to engage users conversationally.
- Interactive queries to refine and personalize recommendations.
- Support for multiple languages to broaden accessibility.

### **Recommendation Engine:**
- Collaborative filtering to suggest resources based on similar users' preferences.
- Content-based filtering to tailor suggestions based on user-specific inputs.
- Categorized results for books, videos, articles, and online courses.

---

## **Data Sources**

To ensure a diverse and high-quality dataset, LearnMate will gather data from multiple sources, including:
- **Kaggle**: Use pre-existing datasets such as educational video metadata, eBook collections, and course details.
- **Open Educational Resources (OER)**: Collect freely available textbooks, articles, and academic materials.
- **YouTube**: Scrape metadata for educational videos using APIs.
- **Custom User Feedback**: Build a growing dataset through chatbot interactions and user-submitted preferences.

Data preprocessing will include cleaning, deduplication, feature extraction, and standardization to ensure high-quality inputs for machine learning models.

---

## **Technical Details**

1. **Data Preparation**:
   - Use Kaggle datasets to bootstrap the system with initial resources.
   - Clean and preprocess data to handle missing values, normalize formats, and remove duplicates.
   - Perform feature engineering to extract key attributes, such as resource difficulty level, category, and relevance.

2. **Machine Learning Algorithms**:
   - Implement hybrid recommendation techniques: collaborative filtering, content-based filtering, and ensemble methods.
   - Use NLP models (e.g., BERT) for understanding user queries and matching resources effectively.

3. **Deployment**:
   - Host the application on a scalable cloud platform (e.g., AWS, GCP, or Azure).
   - Develop a web-based frontend using Vue.js and connect it to the backend API built with FastAPI.
   - Containerize services using Docker to ensure scalability and portability.

4. **MLOps**:
   - Automate testing and CI/CD pipelines to ensure continuous model updates and deployment.
   - Monitor the application's performance using tools like Prometheus and Grafana.
   - Implement version control for models and dependencies to maintain reproducibility.

---

## **Roles and Responsibilities**

### **Product Manager (PM):**
- Define the project vision, objectives, and milestones.
- Serve as the point of communication between team members and stakeholders.
- Oversee progress, resolve bottlenecks, and ensure alignment with deliverables.
- Develop the business model and marketing strategy for LearnMate.

### **Data Engineer(s):**
- Collect data from Kaggle, OER, and APIs (YouTube, etc.).
- Set up and maintain data pipelines for ingestion, transformation, and storage.
- Handle data cleaning, feature engineering, and ensure data quality.
- Ensure efficient and scalable data storage solutions (e.g., cloud storage or databases).

### **Data Scientist(s):**
- Analyze cleaned data to identify patterns and insights for feature extraction.
- Develop and train machine learning models for recommendations (collaborative and content-based filtering).
- Fine-tune NLP models to enhance chatbot interactions and improve resource matching.

### **Machine Learning Engineer(s):**
- Integrate machine learning models into the chatbot and recommendation system.
- Optimize models for real-time performance and scalability.
- Work with data scientists to implement ensemble techniques for hybrid recommendations.

### **MLOps Engineer(s):**
- Set up CI/CD pipelines for automated testing, deployment, and monitoring.
- Implement model versioning and rollback capabilities to maintain stability.
- Monitor system performance metrics, including latency, accuracy, and reliability.
- Ensure automated retraining workflows for the recommendation engine based on new data.

### **Frontend Developer(s):**
- Design and build a responsive web interface using Vue.js.
- Create an intuitive user experience for chatbot interactions and displaying recommendations.

### **Backend Developer(s):**
- Develop the backend API for handling user requests and serving recommendations.
- Ensure secure and efficient data exchange between frontend and backend.

---

## **Milestones**

### **Week 1-3:**
- Finalize the problem statement and objectives.
- Gather data from Kaggle, OER, and APIs.
- Set up data ingestion pipelines.
- **Deliverable**: Initial dataset and a working pipeline for data collection.

### **Week 4-6:**
- Clean and preprocess the collected data.
- Extract features and perform exploratory data analysis (EDA).
- Begin development of the chatbot and recommendation engine.
- **Deliverable**: Clean dataset and initial chatbot prototype.

### **Week 7-9:**
- Train and test recommendation models using K-fold cross-validation.
- Integrate chatbot with recommendation engine for seamless interaction.
- **Deliverable**: Functional chatbot integrated with a recommendation engine.

### **Week 10-12:**
- Deploy the application on a cloud platform.
- Set up CI/CD pipelines and monitoring tools.
- Conduct end-to-end testing for deployment readiness.
- **Deliverable**: Fully deployed solution with automated monitoring and updates.

---

## **Expected Outcome**

A user-friendly chatbot and recommendation engine capable of delivering curated learning resources to students, enhancing their learning efficiency and productivity.

---

## **Evaluation Metrics**

- **Recommendation Relevance**: Accuracy of suggestions based on user feedback.
- **Chatbot Performance**: Latency and NLP accuracy in handling user queries.
- **User Satisfaction**: Feedback collected post-interaction.
- **Scalability**: Ability to handle multiple users simultaneously without performance degradation.

# LearnMate Chat Response Analysis

This project provides tools for analyzing chat responses from the LearnMate system, with a focus on generating insights for improving chatbot and recommendation systems.

## Project Structure

```
LearnMate/
├── backend/
│   └── data/
│       ├── chat_requests/      # JSON files containing chat request/response data
│       ├── metrics/            # JSONL files with processing metrics
│       └── processed/          # Generated CSV files from data processing
│           └── metadata/       # Metadata for tracking processed files
└── data_processing.py          # Script to process raw data into DataFrames
└── streamlit_eda.py            # Streamlit app for exploratory data analysis
└── setup.py                    # Setup script for directory structure
└── README.md                   # This file
```

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Download NLTK resources (this is also handled automatically by the scripts):

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

3. Set up the project directory structure:

```bash
python setup.py
```

## Running the Project

### Data Processing

The data processing script extracts information from the JSON and JSONL files in the backend/data directory and converts them to pandas DataFrames, then saves them as CSV files for easier analysis.

```bash
python data_processing.py
```

This will:
- Load all chat request JSON files
- Process the metrics JSONL file
- Extract important features and insights
- Save processed data to CSV files in backend/data/processed/

The processing script has been optimized to:
- Track file changes and only process new or modified files
- Maintain metadata to avoid redundant processing
- Merge new data with existing processed data
- Log processing activities for monitoring

### Streamlit Dashboard with Real-time Updates

The Streamlit dashboard provides an interactive interface for exploring the chat data with real-time update capabilities:

```bash
streamlit run streamlit_eda.py
```

#### Real-time Data Features

1. **Automatic Refresh**: Data is refreshed automatically every 60 seconds, ensuring the dashboard displays the latest chat requests.

2. **Manual Refresh Options**:
   - "Refresh Data Now" button: Clears the cache and reloads data without reprocessing
   - "Reprocess All Data" button: Forces a full reprocessing of raw data files

3. **Real-time Stats Panel**: Shows the latest request time, total requests, and recent activity in the last 24 hours

4. **Last Refresh Indicator**: Displays when data was last updated

These features ensure that as new chat requests are added to the backend, the dashboard will reflect these changes without requiring a restart.

## Dashboard Features

The dashboard includes:
- Overview of chat requests and processing metrics
- Analysis of response content, including topics and entities
- User interaction metrics and preferences
- Recommendation system insights

## Analysis Capabilities

The EDA dashboard is specifically focused on providing insights that would be valuable for improving a chatbot or recommendation system:

1. **Topic Analysis**: Extracting and visualizing the most common topics in responses
2. **Entity Recognition**: Identifying educational entities mentioned in responses
3. **User Behavior Patterns**: Analyzing how different users interact with the system
4. **Response Characteristics**: Examining response types, complexity, and content patterns
5. **Recommendation Insights**: Identifying user preferences and topic affinities

## Example Insights

The dashboard can provide valuable insights such as:
- Which topics are most commonly discussed by each user
- What type of responses (study plans, explanations, etc.) each user prefers
- Which educational resources are commonly recommended
- How response complexity varies by user and request type
- Patterns in session duration and user engagement

These insights can be used to improve personalization, content recommendations, and overall system performance.

## Monitoring and Maintenance

The enhanced data processing script includes logging capabilities to track:
- Processing times
- File changes
- Errors during processing
- Data merging operations

Logs are written to `data_processing.log` in the project directory.
