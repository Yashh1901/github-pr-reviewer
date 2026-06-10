FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock* ./

# Install all dependencies including dev (for tests in CI)
RUN uv pip install --system --no-cache .

# Copy rest of the app
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.webhook:app", "--host", "0.0.0.0", "--port", "8000"]