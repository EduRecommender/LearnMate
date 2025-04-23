FROM python:3.11
WORKDIR /app

# install deps
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# copy code + extras
COPY backend/ ./backend/
COPY agents/ ./agents/
COPY data/ ./data/  

# Set working directory to backend
WORKDIR /app/backend

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8002"]