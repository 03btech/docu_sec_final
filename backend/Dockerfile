# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2 and other packages
# (e.g., PostgreSQL client libraries, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
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

# Expose the port on which the FastAPI application will run
EXPOSE 8000

# Command to run the application (using Uvicorn, which fastapi[all] includes)
# --host 0.0.0.0 makes the server accessible from outside the container
# --reload enables hot-reloading for development (remove for production)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]