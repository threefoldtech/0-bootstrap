# Zero-OS Bootstrap Service

The Zero-OS Bootstrap Service is available on [bootstrap.gig.tech](https://bootstrap.gig.tech).

The Zero-OS Bootstrap Service provides you with the following tools to quickly and easily get you started with **always-up-to-date** builds:

- [Kernel builds](#kernel-builds)
- [Boot files](#boot-files)

The actual autobuild service is implemented in the [zero-os/0-autobuilder](https://github.com/zero-os/0-autobuilder) repository, see there for more documentation.

The build process can be monitored here: [build.gig.tech/monitor/](https://build.gig.tech/monitor/).

<a id="kernel-builds"></a>
## Kernel builds

On the Zero-OS Bootstrap Service home page all available kernel builds (commits) are listed.

You'll find them in two sections:
- First, under **/latest-release/**, all most recent builds per branch are listed
- And under **/kernel/** all most recent builds are listed

In both cases the naming notation `g8os-BRANCH-COMMIT.efi` is used.

E.g. in case of `g8os-1.1.0-alpha-sandbox-cleanup-core0-a2564152.efi`:
- the branch name is `1.1.0-alpha-sandbox-cleanup-core0`
- the commit, or build number is `a2564152`

<a id="boot-files"></a>
## Boot files

Next to the most recent kernel builds, the Zero-OS bootstrap service also provides you with all other files to get the kernel booted:

- [ISO file](#iso)
- [USB image](#usb)
- [iPXE script](#ipxe)

<a id="iso"></a>
### ISO

You can request an ISO file (~2MB) which contains a bootable iPXE service which will download the requested kernel.

To generate an ISO, just follow this url: `https://bootstrap.gig.tech/iso/BRANCH/ZEROTIER-NETWORK`

For example, to use the most recent build of the `1.1.0-alpha` branch, with earth's ZeroTier network: `https://bootstrap.gig.tech/iso/1.1.0-alpha/8056c2e21c000001`

Of course, you can specify a more precise branch (for debugging purposes for instance), e.g.: `https://bootstrap.gig.tech/iso/1.1.0-alpha-changeloglevel-initramfs-035dd483/8056c2e21c000001`

<a id="usb"></a>
### USB

You can also download an USB image, ready to copy to an USB stick: `https://bootstrap.gig.tech/usb/BRANCH/ZEROTIER-NETWORK`

<a id="ipxe"></a>
### iPXE Script

Like for ISO and USB, you can request a iPXE script using: `https://bootstrap.gig.tech/ipxe/BRANCH/ZEROTIER-NETWORK`

This will provide with you with the script that gets generated for, and embedded in the ISO file and the USB image

For instance `https://bootstrap.gig.tech/ipxe/zero-os-master/hello/extra%20argument`:
```
#!ipxe
dhcp
chain https://bootstrap.gig.tech/kernel/zero-os-master.efi zerotier=hello extra argument
```

This is useful when you want to boot a remote machine using an iPXE script, i.e. `Packet.net` or `OVH` servers.
