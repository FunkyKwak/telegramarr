# Base image
FROM python:3.11-slim

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /app
COPY app/main.py /app/main.py
RUN chmod +x /app/main.py

# Run the main script
CMD ["python", "app/main.py"]
