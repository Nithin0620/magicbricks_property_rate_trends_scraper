FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/stage1 data/stage2 data/stage3 data/stage4

ENTRYPOINT ["python", "pipeline.py"]
