#!/bin/bash
set -e

template="/opt/ipxe-template"
templateuefi="/opt/ipxe-template-uefi"
makeopts="-j 10"

echo "[+] preparing ipxe template on: ${template}"
pushd /tmp

echo "[+] clean up previous stuff"
rm -rf ipxe
rm -rf ipxe-legacy
rm -rf ipxe-uefi

echo "[+] downloading source code"
git clone https://github.com/threefoldtech/ipxe

# download let's encrypt root certificates
pushd ipxe/src
wget https://letsencrypt.org/certs/lets-encrypt-r3-cross-signed.pem
wget https://letsencrypt.org/certs/lets-encrypt-r3.pem
wget https://letsencrypt.org/certs/isrgrootx1.pem
popd

mkcert="isrgrootx1.pem,lets-encrypt-r3-cross-signed.pem,lets-encrypt-r3.pem"
mktrust=${mkcert}

echo "[+] preparing images"
cp -r ipxe ipxe-legacy
cp -r ipxe ipxe-uefi

echo "[+] pre-compiling: ipxe-legacy"
pushd ipxe-legacy/src
make ${makeopts} bin/ipxe.iso CERT=${mkcert} TRUST=${mktrust}
make ${makeopts} bin/ipxe.usb CERT=${mkcert} TRUST=${mktrust}
make ${makeopts} bin/ipxe.lkrn CERT=${mkcert} TRUST=${mktrust}
popd

echo "[+] pre-compiling: ipxe-uefi"
pushd ipxe-uefi/src
make ${makeopts} bin-x86_64-efi/ipxe.efi CERT=${mkcert} TRUST=${mktrust}
popd

echo "[+] removing previous installation"
rm -rf ${template}
rm -rf ${templateuefi}

echo "[+] installing templates"
cp -ar ipxe-legacy/src ${template}
cp -ar ipxe-uefi/src ${templateuefi}

echo "[+] ================================================================"
echo "[+] ipxe legacy template installed on: ${template}"
echo "[+] ipxe uefi template installed on: ${templateuefi}"
echo "[+] ================================================================"
