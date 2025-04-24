# LearnMate

### Web App Links:
- Recommendation System: [Link](https://learnmate.streamlit.app/)
- EDA + Data Vizualization for Data Scientists: [Link](https://learnmate-eda.streamlit.app)

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
- Andrés Taboada

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
- Collaborative filtering to suggest resources based on similar users’ preferences.
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
   - Monitor the application’s performance using tools like Prometheus and Grafana.
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
