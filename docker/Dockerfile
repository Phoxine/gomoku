FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.7

COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --locked --no-install-project \
    && /usr/local/bin/python -m pip uninstall --yes pip setuptools

COPY src/ ./src/

CMD ["sh", "-c", "while :; do sleep 3600; done"]
