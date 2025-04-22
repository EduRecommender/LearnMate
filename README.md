# LearnMate

### Web App Links:
- Recommendation System: [Link](https://learnmate.streamlit.app/)
- EDA + Data Vizualization for Data Scientists: [Link](https://learnmate-eda.streamlit.app)

## **Project Setup Instructions**

### Prerequisites
- Node.js and npm
- Python 3.x
- Ollama (https://ollama.com/)

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run the backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### LLM Setup (Ollama)
```bash
# Start Ollama service (in a separate terminal)
ollama serve

# In another terminal, run the LLM model
ollama run llama3:8b
```

Note: Make sure all three components (frontend, backend, and Ollama) are running simultaneously for the application to work properly.

