FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /2296-bot

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY config/requirements.txt requirements.txt
RUN sed -i 's/Requests/requests/' requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "-m", "bot.launcher"]
