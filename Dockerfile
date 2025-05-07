# 1. Choose a base Python image
FROM python:3.10-slim

# 2. Set environment variables for Python for best practices in Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set up the working directory in the container
WORKDIR /app

# 4. Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# 5. Install Python dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy all your application code into the working directory
# Copy top-level Python files
COPY __init__.py .
COPY config.py .
COPY database.py .
COPY main.py .
COPY models.py .
COPY services.py .

# Copy subdirectories
COPY core ./core
COPY routers ./routers

# 7. Expose the port your application runs on (as defined in main.py for Uvicorn)
EXPOSE 8000

# 8. Define the command to run your application
# IMPORTANT: You will need to pass the SUPABASE_URL, SUPABASE_SERVICE_KEY,
# and GEMINI_API_KEY environment variables when running the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]