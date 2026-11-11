FROM python:3.14-slim

WORKDIR /workspace

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.7

COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --locked --no-install-project

COPY src/ ./src/

CMD ["sh", "-c", "while :; do sleep 3600; done"]
