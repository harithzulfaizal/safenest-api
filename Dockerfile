# 1. Choose a base Python image
FROM python:3.12-slim

# 2. Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set up the working directory
WORKDIR /app

# 4. Copy requirements.txt
COPY requirements.txt .

# 5. (OPTIONAL - FOR DEBUGGING) Install common build dependencies
# If pip errors indicate missing compilers or dev headers, uncomment the next lines:
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     build-essential \
#     libffi-dev \
#     python3-dev && \
#     rm -rf /var/lib/apt/lists/*

# 6. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy all your application code
COPY __init__.py .
COPY config.py .
COPY database.py .
COPY main.py .
COPY models.py .
COPY services.py .
COPY core ./core
COPY routers ./routers

# 8. Expose the port
EXPOSE 8000

# 9. Define the command to run your application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]