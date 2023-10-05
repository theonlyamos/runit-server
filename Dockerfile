FROM ubuntu:22.04

LABEL maintainer="Amos Amissah"

ENV TZ=UTC

WORKDIR /app/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update \
    && apt-get install -y gnupg gosu curl ca-certificates zip unzip git supervisor \
       sqlite3 libcap2-bin libpng-dev python3 python3-dev python3-venv \
    && curl https://bootstrap.pypa.io/get-pip.py | python3

RUN mkdir -p ~/.gnupg \
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
      php8.2-readline php8.2-ldap mysql-client \
      libmysqlclient-dev \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

RUN curl https://bun.sh/install | bash 

RUN echo 'export BUN_PATH="$HOME/.bun"' >> $HOME/.bashrc \
    && echo 'export PATH="$PATH:$BUN_PATH"' >> $HOME/.bashrc

RUN python3 -m pip install python-dotenv

RUN bun add -g dotenv 

RUN setcap "cap_net_bind_service=+ep" /usr/bin/php8.2

RUN ln -s /usr/bin/python

RUN ln -s /usr/bin/python3 /usr/bin/python

COPY . /app/

RUN mv .env.production .env

RUN pip install -e .

EXPOSE 9000

# RUN ln -sf /bin/bash /bin/sh

ENTRYPOINT ["runit-server", "--production"]
