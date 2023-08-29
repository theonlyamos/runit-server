FROM python:3-alpine

LABEL maintainer="Amos Amissah<theonlyamos@gmail.com>"

ENV TZ=UTC

WORKDIR /app/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python"]