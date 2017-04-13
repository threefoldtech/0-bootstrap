# G8OS Bootstrap
This is a webservice which will provide dynamic construction of iPXE scripts for booting and bootstrapping G8OS Kernel Images

# Installation
To speedup ISO creation, the script will use a iPXE-template directory which contains a pre-compiled version of the sources.

To pre-compile code, you can run the `setup/template.sh` script.
This will prepare the template and put it on `/opt/ipxe-template`.

In oder to compile correctly the sources, you'll need (ubuntu): `build-essential syslinux liblzma-dev libz-dev genisoimage`

# Run
This is a `Flask` webservice, just run the `bootstrap.py` server file.

Kernel images will be served from `kernel` directory. Images are in form: `g8os-BRANCH-ARCH.efi`

