FROM python:3.11-slim

# Minimal system dependencies only (no Chromium — Crawl4AI runs on the VM)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline source
COPY . .

# Create runtime directories
RUN mkdir -p output/final crawl_cache logs

# Default: full pipeline run
CMD ["python", "main.py"]
