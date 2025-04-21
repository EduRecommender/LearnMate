# LearnMate EDA Dashboard

This directory contains the LearnMate Chat Response Analysis dashboard built with Streamlit. It provides insights into chat responses for improving the chatbot and recommendation systems.

## Project Structure

```
eda/
├── streamlit_eda.py         # Main Streamlit app for exploratory data analysis
├── streamlit_app.py         # Streamlit app entry point with setup procedures
├── data_processing.py       # Script to process raw data into DataFrames
├── requirements.txt         # Required dependencies for the EDA dashboard
├── .streamlit/              # Streamlit configuration
└── backend/                 # Data directory
    └── data/
        ├── chat_requests/   # JSON files containing chat request/response data
        ├── metrics/         # JSONL files with processing metrics
        └── processed/       # Generated CSV files from data processing
            └── metadata/    # Metadata for tracking processed files
```

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
cd eda
streamlit run streamlit_eda.py
```

## Features

The dashboard includes:
- Overview of chat requests and processing metrics
- Analysis of response content, including topics and entities
- User interaction metrics and preferences
- Recommendation system insights
- Real-time updates and data refreshing

## Deployment

The dashboard is configured for deployment on Streamlit Cloud. A GitHub Actions workflow ensures the repository is ready for deployment.

To deploy:
1. Go to https://share.streamlit.io/
2. Connect your repository
3. Set the main file path to `eda/streamlit_eda.py` 