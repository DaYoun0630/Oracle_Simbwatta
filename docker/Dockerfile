FROM python:3.10-slim-bookworm

# Install UV (fast Python package manager)
RUN pip install --no-cache-dir uv

# App directory inside the container
WORKDIR /app

# Copy dependency files first for better caching
COPY src/gpt/pyproject.toml src/gpt/uv.lock ./
RUN uv sync --frozen

# Copy application code
COPY src/gpt/app ./app

# Expose the app port
EXPOSE 8000
# Start FastAPI via Uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
