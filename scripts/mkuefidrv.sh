#!/bin/bash
if [ "$1" == "" ]; then
    echo "[-] missing root path"
    exit 1
fi

if [ "$2" == "" ]; then
    echo "[-] missing pciref"
    exit 1
fi

root="$1"
pciref="$2"

echo "[+] root is: ${root}"
echo "[+] pci ref: ${pciref}"

cat ${root}/boot.ipxe

pushd ${root}/src

MKCERT="isrgrootx1.pem,lets-encrypt-r3.pem,lets-encrypt-r3-cross-signed.pem"
MKTRUST=${MKCERT}

make bin-x86_64-efi/${pciref}.efidrv EMBED=${root}/boot.ipxe CERT=${MKCERT} TRUST=${MKTRUST}

cp bin-x86_64-efi/${pciref}.efidrv ${root}/ipxe.efidrv
