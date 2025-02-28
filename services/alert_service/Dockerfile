FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir watchdog

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]
