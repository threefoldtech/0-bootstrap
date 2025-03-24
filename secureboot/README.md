# SecureBoot Bootstrap (with Signed UEFI Driver)
- Compile and Sign iPXE EFI Driver for specific PCI `Vendor:Product`
- Boot patched EFI Shell from `threefold/edk2` (branch `efishell-driver-reconnect`)
- Apply `threefold.nsh` to install Signed EFI Driver
