# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY start.sh .

RUN chmod +x start.sh

# Ensure data directory
RUN mkdir -p /app/data

# Expose nothing by default
EXPOSE 8000

# Run the main script
CMD ["./start.sh"]