FROM oven/bun

LABEL maintainer="Amos Amissah<theonlyamos@gmail.com>"

ENV TZ=UTC

WORKDIR /app/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /app/

RUN bun install 

ENTRYPOINT ["bun", "run"]