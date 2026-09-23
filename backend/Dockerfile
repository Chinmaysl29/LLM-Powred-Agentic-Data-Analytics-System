FROM python:3.11-slim

# System dependencies required by psycopg and general build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache optimisation)
COPY requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY . backend/

# Create the uploads directory so the app doesn't crash on first run
RUN mkdir -p datasets/raw

EXPOSE 8000

# --reload enables hot-reload when the source volume is mounted
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
