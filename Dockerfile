FROM python:3.11-slim

WORKDIR /app

# System závislosti
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python závislosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Zdrojový kód
COPY src/ ./src/

# SageMaker očakáva train script na konkrétnom mieste
ENV PYTHONPATH=/app

CMD ["python", "src/train/train.py"]
