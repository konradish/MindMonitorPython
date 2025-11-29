FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Leverage caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"
CMD ["uv", "run", "python", "-m", "consciousness_monitor"]