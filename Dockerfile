FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set up user with UID 1000 (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy backend requirements
COPY --chown=user backend/requirements.txt /app/backend/requirements.txt

# Install python dependencies
# First install CPU-only torch to keep the image slim, then the rest
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the rest of the backend files
COPY --chown=user backend/ /app/backend/

# Set Python path to ensure module resolution works correctly
ENV PYTHONPATH="/app"

# Expose Hugging Face default port
EXPOSE 7860

# Run FastAPI app
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
