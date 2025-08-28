FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    TZ=America/Chicago \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    gnupg \
    dos2unix \
    libmagic1 \
    libmagic-dev \
    file \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /api

# Copy and install Python dependencies first for better caching
COPY requirements.txt /api/requirements.txt
RUN pip3 install --no-cache-dir -r /api/requirements.txt

# Copy the rest of the application
COPY . /api

# Ensure the entrypoint script is executable
RUN chmod +x /api/api_startup.sh

EXPOSE 8000

# Start the FastAPI app (no runtime pip installs)
ENTRYPOINT ["/api/api_startup.sh"]