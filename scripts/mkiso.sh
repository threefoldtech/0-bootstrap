#!/bin/bash
if [ "$1" == "" ]; then
    echo "[-] missing root path"
    exit 1
fi

root="$1"
echo "[+] root is: ${root}"

cat ${root}/boot.ipxe

pushd ${root}/src
make bin/ipxe.iso EMBED=${root}/boot.ipxe

cp bin/ipxe.iso ${root}/
