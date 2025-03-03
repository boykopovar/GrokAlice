FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    libxi6 \
    libgconf-2-4 \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean

WORKDIR /app
COPY requirements.txt .
COPY main.py .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:$PORT"]