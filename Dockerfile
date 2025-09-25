FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY daybot_mcp/ daybot_mcp/
COPY .env.example .env

# Create non-root user
RUN useradd -m -u 1000 daybot && chown -R daybot:daybot /app
USER daybot

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/tools/healthcheck || exit 1

# Run the application
CMD ["uvicorn", "daybot_mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]
