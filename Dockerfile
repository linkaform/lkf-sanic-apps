####################################
# Image for develop                #
####################################
#FROM python:3.7-slim-bullseye as addons-base
# FROM python:3.10.14-bullseye as addons-base
FROM python:3.12.12-slim-trixie AS sanic-base


RUN apt-get update && \
    apt-get -y install \
    curl \
    gcc \
    gpg \
    git \
    libffi-dev \
    libpq-dev \
    poppler-utils \
    procps \
    python3-psycopg2 \
    time \
    unzip \
    vim \
    wget

#mongo 5.0 tools
RUN curl -fsSL https://pgp.mongodb.com/server-6.0.asc | gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor
# trusted=yes: la clave de firma de MongoDB usa una firma SHA1 que Debian trixie rechaza (sqv) desde 2026-02-01
RUN echo "deb [ trusted=yes signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg] http://repo.mongodb.org/apt/debian bullseye/mongodb-org/6.0 main" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list

RUN apt-get update && \
    apt-get -y install \
    mongodb-org-shell \
    mongodb-org-tools

COPY ./secrets/lkf_jwt_key.pub /etc/ssl/certs/lkf_jwt_key.pub
COPY ./lkfpwd.py /usr/local/lib/python3.12


WORKDIR /srv/lkf-sanic-app/

####################################
# Image for develop                #
####################################
FROM  linkaform/sanic-app:base AS develop


RUN pip install --upgrade pip
COPY ./docker/main_entrypoint.sh /usr/local/bin/main_entrypoint.sh
RUN chmod a+x /usr/local/bin/main_entrypoint.sh
COPY ./docker/requires.txt /tmp/

# setuptools>=82 quito pkg_resources, que el setup.py legacy de cx-Oracle 8.3.0 todavia necesita
RUN echo "setuptools<82" > /tmp/build-constraints.txt
ENV PIP_CONSTRAINT=/tmp/build-constraints.txt
RUN pip install -r /tmp/requires.txt
COPY ./bin/lkfaddons.py /usr/local/bin/lkfaddons
RUN chmod a+x /usr/local/bin/lkfaddons

# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#        build-essential \
#        pkg-config \
#     && rm -rf /var/lib/apt/lists/*


RUN pip install git+https://github.com/Bastian-Kuhn/wallet.git
WORKDIR /tmp/
ADD https://f001.backblazeb2.com/file/lkf-resources/backblaze_utils-0.1.tar.gz ./backblaze_utils-0.1.tar.gz 
RUN pip install backblaze_utils-0.1.tar.gz

# RUN echo testsssssss
#RUN git clone https://github.com/linkaform/backblaze_utils.git
#WORKDIR /usr/local/bin/backblaze_utils
RUN rm /tmp/*.tar.gz

RUN adduser --home /srv/lkf-sanic-app/ --uid 1000 --disabled-password nonroot
RUN mkdir -p /srv/lkf-sanic-app/app
RUN chown -R 1000:1000 /srv/lkf-sanic-app
WORKDIR /srv/lkf-sanic-app/app

####
# Oracle Integration
###
WORKDIR /opt/oracle
ADD https://f001.backblazeb2.com/file/app-linkaform/public-client-126/71202/6650c41a967ad190e6a76dd3/66b5974cae333f423347115c.zip  66b5974cae333f423347115c.zip
RUN unzip 66b5974cae333f423347115c.zip
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH

RUN apt-get update && apt-get -y install libaio1t64
RUN echo /opt/oracle/instantclient_12_2 > /etc/ld.so.conf.d/oracle-instantclient.conf
RUN ldconfig

### END ORACLE ###

RUN echo teesttt
WORKDIR /tmp/
ADD  https://f001.backblazeb2.com/file/lkf-resources/linkaform_api-3.0.tar.gz ./linkaform_api-3.0.tar.gz
RUN pip install linkaform_api-3.0.tar.gz

# USER nonroot

WORKDIR /srv/lkf-sanic-app/app

####################################
# Image for prodcution             #
####################################
FROM linkaform/sanic-app:develop AS prod


USER root

# TODO COPIAR TODO ADDONS Y HACER IMAGEN.... AQUI O EN SCIRPTS?
COPY /addons /usr/local/lib/python3.12/site-packages/lkf_addons/
COPY ./ /srv/lkf-sanic-app/
COPY /docker/main_entrypoint.sh /docker/main_entrypoint.sh
RUN chmod a+x /docker/main_entrypoint.sh

#RUN chown -R 33:33 /srv/lkf-sanic-app

# USER www-data

WORKDIR /srv/lkf-sanic-app/app/
CMD ["python", "main.py"]
