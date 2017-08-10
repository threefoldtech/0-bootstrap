# Zero-OS Bootstrap Service

This web service will provides dynamic construction of iPXE scripts for booting and bootstrapping Zero-OS kernel images.

## Endpoints

This web service provides:
- `/ipxe/[branch]/[zerotier]`: generate an iPXE script to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/iso/[branch]/[zerotier]`: generate a bootable ISO to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/usb/[branch]/[zerotier]`: generate a bootable USB image to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/uefi/[branch]/[zerotier]`: generate an UEFI bootloader with a ipxe script to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/uefimg/[branch]/[zerotier]`: same as above, but an image to be dd'd to an usb stick for UEFI boxes
- `/kernel/[name]`: provide a kernel stored

The `/ipxe`, `/iso`, `/usb` and `/uefi`  endpoints provide one more optional options to pass extra kernel argument, eg: `/ipxe/[branch]/[zerotier]/rw quiet`

## Installation

To speedup ISO and USB images creation, the script will use a iPXE-template directory which contains a pre-compiled version of the sources.

To pre-compile code, you can run the `setup/template.sh` script.
This will prepare the template and put it on `/opt/ipxe-template`.

In oder to compile correctly the sources, you'll need (ubuntu): `build-essential syslinux liblzma-dev libz-dev genisoimage isolinux wget dosfstools`

## Run

This is a `Flask` web service, just run the `bootstrap.py` server file. On ubuntu, you'll need `python3-flask`.

Kernel images will be served from `kernel` directory. Images are in form: `zero-os-BRANCH-ARCH.efi`

## Configuration

You can customize the service by editing `config.py`:
- `BASE_HOST`: http web address (eg: https://bootstrap.gig.tech)
- `IPXE_TEMPLATE`: iPXE template path (by default, setup script install it to `/opt/ipxe-template`)
- `KERNEL_PATH`: path where to find kernels
- `HTTP_PORT`: http listen port,
- `DEBUG`: enable (True) or disable (False) debug Flask

## Documentation

For more documentation see the [`/docs`](./docs) directory, where you'll find a [table of contents](/docs/SUMMARY.md).
