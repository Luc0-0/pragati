FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run listens on 8080
EXPOSE 8080

# Use Gunicorn with Uvicorn workers for production
CMD exec uvicorn api.main:app --host 0.0.0.0 --port 8080 --workers 2
