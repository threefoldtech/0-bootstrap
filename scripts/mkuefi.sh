#!/bin/bash
if [ "$1" == "" ]; then
    echo "[-] missing root path"
    exit 1
fi

root="$1"
echo "[+] root is: ${root}"

cat ${root}/boot.ipxe

pushd ${root}/src

MKCERT="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"
MKTRUST="letsencrypt-x3-cross.crt,letsencrypt-x3.crt"

make bin-x86_64-efi/ipxe.efi EMBED=${root}/boot.ipxe CERT=${MKCERT} TRUST=${MKTRUST}


cp bin-x86_64-efi/ipxe.efi ${root}/
