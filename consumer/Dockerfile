FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose metrics port
EXPOSE 8001

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Run the consumer
CMD ["python", "-m", "src.consumer"]
