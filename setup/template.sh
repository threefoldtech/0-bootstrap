#!/bin/bash
set -e

template="/opt/ipxe-template"
templateuefi="/opt/ipxe-template-uefi"

echo "[+] preparing iPXE template on: ${template}"

echo "[+] downloading source code"
pushd /tmp
git clone --depth=1 git://git.ipxe.org/ipxe.git

echo "[+] preparing images"
cp -r ipxe ipxe-legacy
cp -r ipxe ipxe-uefi

for target in "ipxe-legacy" "ipxe-uefi"; do
    echo "[+] preparing: ${target}"
    pushd ${target}/src

    # Enable HTTPS
    sed -i "s/undef\tDOWNLOAD_PROTO_HTTPS/define\tDOWNLOAD_PROTO_HTTPS/" config/general.h

    wget -4 https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem.txt -O letsencrypt-x3-cross.crt
    wget -4 https://letsencrypt.org/certs/letsencryptauthorityx3.pem.txt -O letsencrypt-x3.crt

    popd
done

MKCERT="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"
MKTRUST="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"

echo "[+] pre-compiling: ipxe-legacy"
pushd ipxe-legacy/src
make -j 5 bin/ipxe.iso CERT=${MKCERT} TRUST=${MKTRUST}
make -j 5 bin/ipxe.usb CERT=${MKCERT} TRUST=${MKTRUST}
make -j 5 bin/ipxe.lkrn CERT=${MKCERT} TRUST=${MKTRUST}
popd

echo "[+] pre-compiling: ipxe-uefi"
pushd ipxe-uefi/src
make -j 5 bin-x86_64-efi/ipxe.efi CERT=${MKCERT} TRUST=${MKTRUST}
popd

echo "[+] installing templates"
cp -ar ipxe-legacy/src ${template}
cp -ar ipxe-uefi/src ${templateuefi}

echo "[+] ================================================================"
echo "[+] iPXE legacy template installed on: ${template}"
echo "[+] iPXE uefi template installed on: ${templateuefi}"
echo "[+] ================================================================"
