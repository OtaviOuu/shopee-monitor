FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    libnss3 \
    libgconf-2-4 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt


CMD ["python", "shopee_monitor.py"]
