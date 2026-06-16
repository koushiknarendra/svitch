FROM python:3.12-slim

WORKDIR /app

# Copy inference server
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Copy PII Shield and Agent Tracer from repo root
COPY pii-shield/service/detectors ./pii-shield/service/detectors
COPY pii-shield/service/requirements.txt ./pii-shield/service/requirements.txt
RUN pip install --no-cache-dir -r pii-shield/service/requirements.txt

COPY agent-tracer/svitch_tracer ./agent-tracer/svitch_tracer
COPY agent-tracer/__init__.py ./agent-tracer/__init__.py 2>/dev/null || true

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
