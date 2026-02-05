FROM python:3.11-slim

# Install Graphviz - THIS WILL WORK IN DOCKER
RUN apt-get update && apt-get install -y \
    graphviz \
    libgraphviz-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Start command
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:10000", "--workers", "4"]