# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Ensure data directory
RUN mkdir -p /app/data

# Expose port Flask/Gunicorn
EXPOSE 8000

# Start both scripts in parallel
CMD ["/bin/sh", "-c", "python worker.py & gunicorn --bind 0.0.0.0:8000 api:app"]