FROM python:3.6-alpine

RUN apk update \
    && apk upgrade \
    && apk add bash zip

WORKDIR "/app"
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

ENV LOG=1

CMD ["python", "server.py"]