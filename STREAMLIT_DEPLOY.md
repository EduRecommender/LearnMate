# Deploying LearnMate EDA Dashboard to Streamlit Cloud

This guide explains how to deploy the LearnMate EDA Dashboard to Streamlit Cloud.

## Prerequisites

- A GitHub account
- Repository access

## Deployment Steps

1. **Push your code to GitHub**

   Make sure your code is pushed to the repository, especially the following files:
   - `streamlit_eda.py` - The main Streamlit app
   - `streamlit_requirements.txt` - The requirements file for Streamlit Cloud
   - `setup.py` - Script to set up the project directory structure
   - `data_processing.py` - Script to process the data

2. **Deploy to Streamlit Cloud**

   a. Go to [Streamlit Cloud](https://share.streamlit.io/)
   
   b. Log in with your GitHub account
   
   c. Click "New app" and select your repository
   
   d. Configure the app:
      - **Main file path**: `streamlit_eda.py`
      - **Requirements file**: `streamlit_requirements.txt`
      - **Python version**: 3.10

   e. Click "Deploy"

3. **Environment Variables (if needed)**

   Add the following environment variables in the Streamlit Cloud settings:
   - `STREAMLIT_SHARING=1` (This tells the app it's running on Streamlit Cloud)

## How This Works

The deployment process emulates what your `run_learnmate_eda.sh` script does locally:

1. Streamlit Cloud sets up a Python environment using `streamlit_requirements.txt`
2. When the app starts, `streamlit_eda.py` is executed
3. The app calls `setup.py` and `data_processing.py` as needed
4. Sample data is generated if no real data exists

## Monitoring and Troubleshooting

- Check the Streamlit Cloud logs for any errors
- If you need to update the deployment, just push changes to your repository

## Notes

- The GitHub Actions workflow `.github/workflows/streamlit-eda-deploy.yml` helps ensure your repository is ready for deployment
- Unlike running locally with the shell script, Streamlit Cloud handles the virtual environment setup automatically
- The app is configured to create necessary directories and sample data when running on Streamlit Cloud 