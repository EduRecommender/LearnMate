# LearnMate Setup Instructions

Follow these steps to set up and run the LearnMate application.

## Prerequisites

- Node.js (for frontend)
- Python 3.12+ (for backend)
- Ollama installed (for the LLM functionality)

## Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install additional required packages:
   ```bash
   pip install python-multipart pydantic-settings
   ```

## Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install the required Node.js packages:
   ```bash
   npm install
   ```

## Running the Application

### 1. Start the Ollama LLM Service

Download and run the Llama 3 model:
```bash
# If not already installed, download Ollama from https://ollama.com/
ollama run llama3:8b
```

### 2. Start the Backend Server

In a new terminal window:
```bash
cd backend
# Activate the virtual environment if needed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### 3. Start the Frontend Development Server

In a new terminal window:
```bash
cd frontend
npm run dev
```

## Accessing the Application

The frontend will be available at: http://localhost:3000

The backend API will be accessible at: http://localhost:8002

## Troubleshooting

- If you encounter module import errors, ensure all dependencies are installed
- Make sure Ollama service is running before starting the backend
- Check the console logs for any specific error messages 