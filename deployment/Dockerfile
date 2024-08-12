FROM ubuntu:22.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y \
        build-essential git libsnappy-dev libz-dev \
        libtar-dev libb2-dev autoconf libtool libjansson-dev \
        libhiredis-dev libsqlite3-dev \
        python3-flask python3-redis python3-docker python3-pytoml \
        libssl-dev python3-pip python3-requests python3-nacl \
        wget sqlite3 \
        syslinux liblzma-dev libz-dev genisoimage \
        isolinux dosfstools udev parted

RUN git clone https://github.com/threefoldtech/0-bootstrap /bootstrap

RUN cd /bootstrap/setup && \
    bash template.sh

RUN cd /bootstrap && \
    cat db/schema.sql | sqlite3 db/bootstrap.sqlite3

RUN cd /bootstrap && \
    cp config.py.sample config.py

RUN rm -rf /var/lib/apt/lists/*

WORKDIR /bootstrap

ENTRYPOINT ["python3", "bootstrap.py"]


