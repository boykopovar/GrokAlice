FROM python:3.11-slim

#RUN apt-get update && apt-get install -y \
#    wget \
#    xvfb \
#    libxi6 \
#    libgconf-2-4 \
#    unattended-upgrades \
#&& wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
#&& apt install -y ./google-chrome-stable_current_amd64.deb \
#&& rm -f google-chrome-stable_current_amd64.deb \
#&& wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#&& echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
#&& echo 'Unattended-Upgrade::Allowed-Origins {"Google LLC:stable";};' > /etc/apt/apt.conf.d/51google-chrome-unattended \
#&& apt-get update \
#&& apt-get clean \
#&& dpkg-reconfigure -f noninteractive unattended-upgrades

WORKDIR /app
COPY requirements.txt .
COPY main.py .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:$PORT --timeout 300"]