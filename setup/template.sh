#!/bin/bash
template="/opt/ipxe-template"

echo "[+] preparing iPXE template on: ${template}"

echo "[+] downloading source code"
pushd /tmp
git clone --depth=1 git://git.ipxe.org/ipxe.git

echo "[+] pre-compiling"
pushd ipxe/src
make -j 5 bin/ipxe.iso

echo "[+] installing template"
popd
cp -ar ipxe/src ${template}

echo "[+] ================================================================"
echo "[+] iPXE template installed on: ${template}"
echo "[+] ================================================================"
