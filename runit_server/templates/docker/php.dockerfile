FROM php:8.2-cli-alpine

LABEL maintainer="Amos Amissah<theonlyamos@gmail.com>"

ENV TZ=UTC

WORKDIR /app/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apk --update add --no-cache php8.2-dev \
       php8.2-pgsql php8.2-sqlite3 php8.2-gd \
       php8.2-curl \
       php8.2-imap php8.2-mysql php8.2-mbstring \
       php8.2-xml php8.2-zip php8.2-bcmath php8.2-soap \
       php8.2-readline php8.2-ldap \
       php8.2-dom --repository http://nl.alpinelinux.org/alpine/edge/testing/ && rm /var/cache/apk/*

RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/bin --filename=composer 

COPY . /app/

RUN composer install

ENTRYPOINT ["php"]