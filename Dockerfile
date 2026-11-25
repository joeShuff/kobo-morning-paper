FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/London

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent state and incoming source files are mounted at /data.
RUN mkdir -p /data

CMD ["python", "scripts/kobo-scheduler.py"]
