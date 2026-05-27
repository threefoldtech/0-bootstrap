# ZOS Bootstrap

A network bootstrapping webservice that generates dynamic iPXE scripts, bootable ISO images, USB images, UEFI loaders, and kernel images for bare-metal node provisioning.

## What this is

ZOS Bootstrap provides network bootstrapping capabilities for Zero-OS nodes. It delivers initial configuration and boot images over the network, enabling automated operating system provisioning without manual intervention. The service generates custom boot configurations based on node identity and network parameters.

The webservice is built with Flask and serves as the entry point for nodes joining the infrastructure, producing iPXE scripts, ISO files, USB images, UEFI bootloaders, and directly-bootable kernels on demand.

## What this repository contains

- `bootstrap.py` — Flask web service that handles boot image generation
- `config.py` — Service configuration (networks, paths, ports)
- `setup/template.sh` — Pre-compilation script for iPXE templates
- `db/schema.sql` — SQLite schema for runtime provisioning database
- `kernel/` — Directory for kernel images (`zero-os-BRANCH-ARCH.efi`)

## Role in the stack

## ZOS / Zero-OS

ZOS, also known as Zero-OS, is the operating system layer used to run and manage nodes. It provides the low-level runtime environment for workloads, networking, storage, and automation.

ZOS Bootstrap is the first service a bare-metal node contacts when joining the network. It produces the correct boot artifacts so that ZOS can be fetched and started automatically. The service supports multiple environments (production, test, development, QA) via configurable network profiles.

## Relation to ThreeFold

This technology is used within the ThreeFold ecosystem and was first deployed on the ThreeFold Grid. The component itself is designed as reusable infrastructure technology and should be understood by its technical function first, independent of any specific deployment.

## Ownership

This repository is owned and maintained by TF-Tech NV, a Belgian company responsible for the development and maintenance of this technology.

## Endpoints

The most simple endpoint is the plain text version:
- `/ipxe/`: generate an iPXE plain text script to boot

You can generate a bootable image with a bundle boot-script via:
- `/iso/`: generate a bootable ISO file
- `/usb/`: generate a bootable USB image file
- `/uefi/`: generate a UEFI bootloader file
- `/uefimg/`: same as above, but an image to be dd'd to a USB stick for UEFI boxes
- `/krn/`: generate a directly-bootable kernel

Static targets:
- `/krn-generic`: build a generic iPXE kernel, with SSL certificates authorized
- `/uefi-generic`: build a generic iPXE UEFI bootable image, with SSL certificates authorized
- `/krn-provision`: build a generic iPXE kernel, calling the provisioning endpoint with NIC MAC address
- `/uefi-provision`: build a generic iPXE UEFI bootable, calling the provisioning endpoint with NIC MAC address
- `/kernel/[name]`: provide the kernel (static file)

### Arguments

All endpoints (except `/krn-generic/` and `/kernel/` which are static) accept optional arguments:

```
...endpoint/target/[farmer-id]/[extra-arguments]
```

Target can be one of the following to specify the environment:
- `prod`: production environment
- `test`: testnet environment
- `dev`: devnet environment
- `qa`: quality-assurance special dedicated network

These networks are configurable via `config.py`. The dictionary pointed to by `runmode` should contain a short keyword and define a long pretty name.

By default, these networks have links inside the `kernel-net-path` config location. This directory should contain files called `prod.efi`, `test.efi`, `dev.efi`, and `qa.efi`. These files are used as the default kernel per network.

This provides flexibility for kernel updates and allows different kernels to serve different networks, so testnet can use a test kernel while production stays stable. Using symlinks is recommended (`prod.efi` can be a symlink to the current kernel version).

Any `[argument]` is optional, but arguments are ordered and dependent (you cannot provide extra arguments without providing the farmer-id and network).

Valid endpoint examples:
- `/ipxe/prod`
- `/ipxe/test/1234`
- `/ipxe/dev/5550/console=ttyS0`

### Extra Arguments

Everything set in the last argument is forwarded as-is to the kernel argument line.

## Installation

To speed up ISO and USB image creation, the script uses an iPXE template directory containing a pre-compiled version of the sources.

To pre-compile, run the `setup/template.sh` script. This prepares the template and places it at `/opt/ipxe-template`.

Build dependencies (Ubuntu): `build-essential syslinux liblzma-dev libz-dev genisoimage isolinux wget dosfstools udev`

### Database

Clients can be provisioned at runtime using a database. You need to create the database, even if it is empty:

```bash
cat db/schema.sql | sqlite3 db/bootstrap.sqlite3
```

## Run

This is a Flask web service. Run the `bootstrap.py` server file. On Ubuntu you will need `python3-flask`.

Kernel images are served from the `kernel` directory. Images are in the form: `zero-os-BRANCH-ARCH.efi`

## Configuration

You can customize the service by editing `config.py`:
- `base-host`: HTTP web address (e.g., `https://bootstrap.grid.tf`)
- `ipxe-template`: iPXE template path (default: `/opt/ipxe-template`)
- `ipxe-template-uefi`: iPXE UEFI template path (default: `/opt/ipxe-template-uefi`)
- `kernel-path`: path where to find kernels
- `http-port`: HTTP listen port
- `debug`: enable (`True`) or disable (`False`) Flask debug mode

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.
Copyright (c) TF-Tech NV.
