#!/bin/bash
if [ "$1" == "" ]; then
    echo "[-] missing root path"
    exit 1
fi

root="$1"
echo "[+] root is: ${root}"

cat ${root}/boot.ipxe

pushd ${root}/src

MKCERT="isrgrootx1.pem,lets-encrypt-r3.pem,lets-encrypt-r3-cross-signed.pem"
MKTRUST=${MKCERT}

# make bin/ipxe.lkrn DEBUG=x509 EMBED=${root}/boot.ipxe CERT=${MKCERT} TRUST=${MKTRUST}
make bin/ipxe.lkrn EMBED=${root}/boot.ipxe CERT=${MKCERT} TRUST=${MKTRUST}

cp bin/ipxe.lkrn ${root}/
