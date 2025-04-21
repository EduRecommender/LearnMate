# Deploying LearnMate EDA Dashboard to Streamlit Cloud

This guide explains how to deploy the LearnMate EDA Dashboard to Streamlit Cloud.

## Prerequisites

- A GitHub account
- Repository access

## Deployment Steps

1. **Push your code to GitHub**

   Make sure your code is pushed to the repository, especially the following files:
   - `streamlit_app.py` - The main entry point for Streamlit Cloud
   - `streamlit_eda.py` - The actual Streamlit app
   - `requirements-minimal.txt` - The minimal requirements file for Streamlit Cloud
   - `setup.py` - Script to set up the project directory structure
   - `data_processing.py` - Script to process the data

2. **Deploy to Streamlit Cloud**

   a. Go to [Streamlit Cloud](https://share.streamlit.io/)
   
   b. Log in with your GitHub account
   
   c. Click "New app" and select your repository
   
   d. Configure the app:
      - **Main file path**: `streamlit_app.py`
      - **Requirements file**: `requirements-minimal.txt`
      - **Python version**: 3.9 (recommended for best compatibility)

   e. Click "Deploy"

## How This Works

The deployment process works as follows:

1. Streamlit Cloud sets up a Python environment using `requirements-minimal.txt`, which contains only the essential packages
2. When the app starts, `streamlit_app.py` is executed, which:
   - Creates all necessary directories
   - Sets up the environment variables
   - Imports and runs the main function from `streamlit_eda.py`
3. Sample data is generated if no real data exists

## Troubleshooting

If you encounter dependency issues:

1. Check the Streamlit Cloud logs for specific errors
2. Try reducing the package versions in `requirements-minimal.txt` further
3. Use `streamlit_app.py` as the main entry point instead of directly running `streamlit_eda.py`

## Local Development vs Cloud Deployment

- For local development, use the `run_learnmate_eda.sh` script with `requirements-dev.txt`
- For cloud deployment, use `streamlit_app.py` with `requirements-minimal.txt`

This separation ensures that you can use the latest packages locally while maintaining compatibility with Streamlit Cloud's environment.

## Monitoring and Troubleshooting

- Check the Streamlit Cloud logs for any errors
- If you need to update the deployment, just push changes to your repository

## Notes

- The GitHub Actions workflow `.github/workflows/streamlit-eda-deploy.yml` helps ensure your repository is ready for deployment
- Unlike running locally with the shell script, Streamlit Cloud handles the virtual environment setup automatically
- The app is configured to create necessary directories and sample data when running on Streamlit Cloud 