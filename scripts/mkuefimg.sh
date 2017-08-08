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

# create a loop device to hold partitions and UEFI data
dd if=/dev/zero of=${root}/uefimg.img bs=512 count=4k # large ee-nuff ?

parted ${root}/uefimg.img -s "mklabel msdos mkpart primary fat16 0 100%"
LOOP=$(losetup --partscan --find --show ${root}/uefimg.img)
DIR=$(mktemp -d)
mkfs.vfat ${LOOP}p1
mount ${LOOP}p1 ${DIR}
mkdir -p ${DIR}/EFI/BOOT
cp bin-x86_64-efi/ipxe.efi ${DIR}/EFI/BOOT/BOOTX64.EFI
umount ${DIR}
losetup -d ${LOOP}
[[ -d "${DIR}" ]] && rm -rf ${DIR} || echo "ERROR: WE SHOULDN't get here"


# cp bin-x86_64-efi/ipxe.efi ${root}/
