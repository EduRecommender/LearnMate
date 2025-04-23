FROM python:3.11
WORKDIR /app

# install deps
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# copy code + extras
COPY backend/       .
COPY data/          data/
COPY agents/        agents/

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8002"]