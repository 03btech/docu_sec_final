# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# - build-essential/gcc: for compiling asyncpg Cython extensions
# - curl: required for Docker Compose healthcheck (curl -f http://localhost:8000/health)
# - libpq-dev removed: was needed for psycopg2-binary (now using asyncpg)
RUN apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file first to leverage Docker cache
# This means if requirements.txt doesn't change, this layer is cached
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire FastAPI application code into the container
# Ensure this matches your actual structure, e.g., the 'app' folder
COPY ./app /app/app
COPY ./ml /app/ml
COPY ./seed_data.py /app/seed_data.py

# Expose the port on which the FastAPI application will run
EXPOSE 8000

# Command to run the application
# --reload REMOVED for production. Use docker-compose.override.yml for dev:
#   command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]