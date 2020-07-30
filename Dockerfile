FROM python:3.8-slim

ADD VERSION .

COPY . /app
WORKDIR /app

RUN apt update
RUN apt install git -y
RUN pip install -r requirements.txt

ARG TOKEN
ENV DISCORD_BOT_TOKEN=$TOKEN

CMD ["python3","app.py"]
