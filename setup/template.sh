#!/bin/bash
set -e

template="/opt/ipxe-template"

echo "[+] preparing iPXE template on: ${template}"

echo "[+] downloading source code"
pushd /tmp
git clone --depth=1 git://git.ipxe.org/ipxe.git

echo "[+] pre-compiling"
pushd ipxe/src

# Enable HTTPS
sed -i "s/undef\tDOWNLOAD_PROTO_HTTPS/define\tDOWNLOAD_PROTO_HTTPS/" config/general.h

wget https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem.txt -O letsencrypt-x3-cross.crt
wget https://letsencrypt.org/certs/letsencryptauthorityx3.pem.txt -O letsencrypt-x3.crt

MKCERT="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"
MKTRUST="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"

make -j 5 bin/ipxe.iso CERT=${MKCERT} TRUST=${MKTRUST}
make -j 5 bin/ipxe.usb CERT=${MKCERT} TRUST=${MKTRUST}

echo "[+] installing template"
popd
cp -ar ipxe/src ${template}

echo "[+] ================================================================"
echo "[+] iPXE template installed on: ${template}"
echo "[+] ================================================================"
