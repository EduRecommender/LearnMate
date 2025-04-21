#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}LearnMate EDA Pipeline Start${NC}"
echo -e "${BLUE}============================================${NC}"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}Python is not installed. Please install Python 3.8+ and try again.${NC}"
    exit 1
fi

# Check if virtualenv exists, create if not
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python -m venv .venv
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}Virtual environment activated.${NC}"

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed.${NC}"

# Set up project structure
echo -e "${BLUE}Setting up project structure...${NC}"
python setup.py
echo -e "${GREEN}Project structure setup complete.${NC}"

# Run data processing script
echo -e "${BLUE}Processing data...${NC}"
python data_processing.py
echo -e "${GREEN}Data processing complete.${NC}"

# Check if background mode is requested
if [ "$1" == "--background" ]; then
    echo -e "${BLUE}Starting Streamlit in background mode...${NC}"
    nohup streamlit run streamlit_eda.py > streamlit.log 2>&1 &
    echo -e "${GREEN}Streamlit started in background. Check streamlit.log for details.${NC}"
    echo -e "${GREEN}Access the dashboard at: http://localhost:8501${NC}"
else
    # Run Streamlit app
    echo -e "${BLUE}Starting Streamlit dashboard...${NC}"
    echo -e "${GREEN}Access the dashboard at: http://localhost:8501${NC}"
    streamlit run streamlit_eda.py
fi

echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}LearnMate EDA Pipeline Complete${NC}"
echo -e "${BLUE}============================================${NC}" 