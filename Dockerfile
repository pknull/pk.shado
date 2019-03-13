FROM python:3.6-alpine

ADD VERSION .

RUN apk add --update \
    git \
    openssh \
    gcc gfortran python python-dev py-pip build-base wget freetype-dev libpng-dev openblas-dev

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python","app.py"]
