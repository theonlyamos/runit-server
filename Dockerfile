FROM ubuntu:22.10

LABEL maintainer="Amos Amissah"

ENV TZ=UTC

WORKDIR /app/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update \
    && apt-get install -y gnupg gosu curl ca-certificates zip unzip git supervisor \
       sqlite3 libcap2-bin libpng-dev python3.10 python3-dev \
    && curl https://bootstrap.pypa.io/get-pip.py | python3.10 \
    && mkdir -p ~/.gnupg \
    && chmod 600 ~/.gnupg \
    && echo "disable-ipv6" >> ~/.gnupg/dirmngr.conf \
    && echo "keyserver hkp://keyserver.ubuntu.com:80" >> ~/.gnupg/dirmngr.conf \
    && gpg --recv-key 0x14aa40ec0831756756d7f66c4f4ea0aae5267a6c \
    && gpg --export 0x14aa40ec0831756756d7f66c4f4ea0aae5267a6c > /usr/share/keyrings/ppa_ondrej_php.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/ppa_ondrej_php.gpg] https://ppa.launchpadcontent.net/ondrej/php/ubuntu jammy main" > /etc/apt/sources.list.d/ppa_ondrej_php.list \
    && apt-get update \
    && apt-get install -y php8.2-cli php8.2-dev \
       php8.2-pgsql php8.2-sqlite3 php8.2-gd \
       php8.2-curl \
       php8.2-imap php8.2-mysql php8.2-mbstring \
       php8.2-xml php8.2-zip php8.2-bcmath php8.2-soap \
       php8.2-readline php8.2-ldap \
    #    php8.2-msgpack php8.2-igbinary php8.2-redis php8.2-swoole \
    #    php8.2-memcached php8.2-pcov php8.2-xdebug \
    && curl https://bun.sh/install | bash \
    && echo 'export $BUN_PATH="$HOME:/.bun"' >> $HOME/.bashrc \
    && echo 'export $PATH="$PATH:$BUN_PATH"' >> $HOME/.bashrc \
    && apt-get install -y mysql-client \
    && apt-get install -y libmysqlclient-dev \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN setcap "cap_net_bind_service=+ep" /usr/bin/php8.2

COPY . /app/

RUN mv .env.development .env

RUN python3 -m pip install .

EXPOSE 9000

ENTRYPOINT ["runit-server"]
