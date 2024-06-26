FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    gnupg \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install SQL Server drivers (Optional: remove if not connecting to SQL Server)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list &&\
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Set time zone 
RUN apt update && apt install tzdata -y
ENV TZ="America/Chicago"

WORKDIR /api

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI app using uvicorn
ENTRYPOINT ["/api/api_startup.sh"]