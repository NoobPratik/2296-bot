FROM python:3.11-slim

WORKDIR /2296-bot

COPY . .

RUN pip install -r requirements.txt

CMD [ "python", "-m", "bot.launcher", '--dev']
