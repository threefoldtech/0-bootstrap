#!/bin/bash
set -e

template="/opt/ipxe-template"
templateuefi="/opt/ipxe-template-uefi"
makeopts="-j 16"

echo "[+] preparing ipxe template on: ${template}"

echo "[+] downloading source code"
pushd /tmp
rm -rf ipxe
git clone --depth=1 https://github.com/gigforks/ipxe

echo "[+] preparing images"
rm -rf ipxe-legacy ipxe-uefi
cp -r ipxe ipxe-legacy
cp -r ipxe ipxe-uefi

mkcert="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"
mktrust="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"

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

echo "[+] installing templates"
cp -ar ipxe-legacy/src ${template}
cp -ar ipxe-uefi/src ${templateuefi}
rm -rf ipxe-legacy ipxe-uefi

echo "[+] ================================================================"
echo "[+] ipxe legacy template installed on: ${template}"
echo "[+] ipxe uefi template installed on: ${templateuefi}"
echo "[+] ================================================================"
