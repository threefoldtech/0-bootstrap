# G8OS Bootstrap
This webservice will provides dynamic construction of iPXE scripts for booting and bootstrapping G8OS Kernel Images.

# Endpoints
This webservice provides:
- `/ipxe/[branch]/[zerotier]`: generate an iPXE script to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/iso/[branch]/[zerotier]`: generate a bootable ISO to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/usb/[branch]/[zerotier]`: generate a bootable USB image to boot `g8os-[branch].efi` kernel with `[zerotier]` network id
- `/kernel/[name]`: provide a kernel stored

The `/ipxe`, `/iso` and `/usb` endpoints provide one more optional options to pass extra kernel argument, eg: `/ipxe/[branch]/[zerotier]/rw quiet`

# Installation
To speedup ISO and USB images creation, the script will use a iPXE-template directory which contains a pre-compiled version of the sources.

To pre-compile code, you can run the `setup/template.sh` script.
This will prepare the template and put it on `/opt/ipxe-template`.

In oder to compile correctly the sources, you'll need (ubuntu): `build-essential syslinux liblzma-dev libz-dev genisoimage isolinux wget`

# Run
This is a `Flask` webservice, just run the `bootstrap.py` server file. On ubuntu, you'll need `python3-flask`.

Kernel images will be served from `kernel` directory. Images are in form: `g8os-BRANCH-ARCH.efi`

# Configuration
You can customize the service by editing `config.py`:
- `BASE_HOST`: http web address (eg: https://bootstrap.gig.tech)
- `IPXE_TEMPLATE`: iPXE template path (by default, setup script install it to `/opt/ipxe-template`)
- `KERNEL_PATH`: path where to find kernels
- `HTTP_PORT`: http listen port,
- `DEBUG`: enable (True) or disable (False) debug Flask

