@echo -off

cls

echo "%B=============================================="
echo "%B==   %VZero-OS Certified Node Bootstrapping   %B=="
echo "%B=============================================="
echo "%N "

# Checking SetupMode UEFI Variable
dmpstore SetupMode -sfo | parse VariableInfo 6 >v setupmode
if %setupmode% == 00 then
  echo "%ESystem is not in Setup Mode"
  echo "%N "
  exit /b 2
endif

echo "Initializing bootstrap"

if not exist %homefilesystem%\DRIVER then
  echo "Error: DRIVER: directory not found"
  goto missing
endif

# Looking for a driver file
ls %homefilesystem%\DRIVER\*.EFIDRV -sfo | parse FileInfo 2 -i 1 >v drvfile

if drvfile == "" then
  echo "Error: no driver found"
  goto missing
endif

if not exist %homefilesystem%\EFI\BOOT\ZOS.EFI then
  echo "Error: EFI\BOOT\ZOS.EFI: file not found"
  goto missing
endif

if not exist %homefilesystem%\EFI\LOCKDOWN.EFI then
  echo "Error: EFI\LOCKDOWN.EFI: file not found"
  goto missing
endif

goto process

:missing
exit /b

:process
echo "Driver found: %B%drvfile% %N"
echo " "

echo "Cleaning Boot"
:bootclean
dmpstore BootOrder > null
if not %lasterror% == 0xE then
  bcfg boot rm 0
  goto bootclean
endif

echo "Cleaning Drivers"
:driverclean
dmpstore DriverOrder > null
if not %lasterror% == 0xE then
  bcfg driver rm 0
  goto driverclean
endif

:installkeys
echo "Installing Secure Boot Keys"

%homefilesystem%\EFI\LOCKDOWN.EFI > null

:installboot
echo "Installing Bootloader"

bcfg boot add 0 %homefilesystem%\EFI\BOOT\ZOS.EFI "Zero-OS Bootloader" > null
bcfg boot add 1 %homefilesystem%\EFI\BOOT\BOOTX64.EFI "Zero-OS UEFI Shell" > null
bcfg boot -opt 0x1 ^"-nostartup^"

:installdriver
echo "Installing Driver"

bcfg driver add 0 %drvfile% NetworkDriver-Signed > null

:finished
echo " "
echo "%VBootstrapping done !"
echo "%N(You still need to enable Secure Boot manually)"
echo " "
echo "Rebooting in 5 seconds..."

stall 5000000
reset
