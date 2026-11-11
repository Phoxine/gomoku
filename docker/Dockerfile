FROM python:3.14-slim

WORKDIR /workspace

RUN pip install --no-cache-dir pytest uv

COPY app/ app/

CMD ["sh", "-c", "while :; do sleep 3600; done"]
