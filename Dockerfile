FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and install them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application files
COPY echoloop/ ./echoloop/

# Expose Streamlit port (Cloud Run defaults to 8080)
EXPOSE 8080

# Environment variables
ENV PORT=8080

# Run the UI app on port 8080
CMD ["uv", "run", "streamlit", "run", "echoloop/ui/main.py", "--server.port=8080", "--server.address=0.0.0.0"]
