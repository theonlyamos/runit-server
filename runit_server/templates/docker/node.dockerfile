FROM node:20-alpine

LABEL maintainer="Amos Amissah<theonlyamos@gmail.com>"

ENV NODE_ENV=production

ENV TZ=UTC

WORKDIR /app/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /app/

RUN npm install

ENTRYPOINT ["node"]