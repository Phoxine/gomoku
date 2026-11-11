FROM python:3.14-slim

WORKDIR /workspace/src

RUN pip install --no-cache-dir pytest pytest-cov uv

COPY src/ .

CMD ["sh", "-c", "while :; do sleep 3600; done"]
