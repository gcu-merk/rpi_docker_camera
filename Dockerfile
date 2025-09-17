FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcamera-apps \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py /app/
RUN chmod +x /app/app.py

ENV OUTPUT_DIR=/captures
VOLUME ["/captures"]

CMD ["python", "/app/app.py"]
