# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Ensure data directory
RUN mkdir -p /app/data

# Expose nothing by default

# Run the main script
CMD ["python", "app/main.py"]
