# Problems in Omarchy Mac images, and our fixes

These come from installing an Omarchy Mac image on the M6 Mac mini. They are about the image, not about the M6. Each fix is a small change you can make to the unpacked root image (mount it with `mount -o loop,subvolid=5 root.img <dir>`; the image keeps `/` in `@`, `/home` in `@home`, `/var/log` in `@log`).

## Fixed filesystem UUIDs

Every image has the same filesystem identity: the same root btrfs UUID, boot ext4 UUID and EFI volume id. If a second disk or an install stick carries the same image, `/dev/disk/by-uuid/<root UUID>` can point at the wrong disk, and an `fstab` that names the filesystem by `UUID=` can mount `/`, `/home` or `/var/log` from it. On our Mac mini the link did point at an install stick once the front USB ports worked.

Fix: give your root image its own UUID before you write it.

```sh
new=$(uuidgen | tr A-F a-f)
# with the image unmounted:
printf 'y\n' | btrfstune -U "$new" root.img
# then, with it mounted, replace the old UUID in etc/fstab and etc/default/limine
```

Or name the root by `PARTUUID=` in `fstab`. A whole-disk filesystem on a stick has no PARTUUID, so it cannot take over.

## `boot.mount` fails on every boot

An image written without the boot and EFI partitions has `/boot` and `/boot/efi` lines in `fstab`. Marking `/boot` with `noauto,nofail` is not enough: systemd makes the mount of `/boot/efi` require the mount of its parent path `/boot`, so an automatic `/boot/efi` pulls in `/boot`, and `/boot` fails ("wrong fs type" when the partition is empty). Mark both lines `noauto,nofail,x-systemd.device-timeout=2s`.

You can check an `fstab` without booting: run `/usr/lib/systemd/system-generators/systemd-fstab-generator` with `SYSTEMD_FSTAB=<file>` and three output directories, and look at `local-fs.target.wants`. Neither `boot.mount` nor `boot-efi.mount` should be there.

## First-boot units remove the login on tty1

The units `omarchy-provision-owner.service` and `omarchy-mac-first-boot.service` carry `Conflicts=getty@tty1.service`. Even when their `ConditionPathExists` skips them, systemd drops `getty@tty1` from the boot transaction. If you auto-login on tty1 and do not use the first-boot flow, mask both units (`ln -s /dev/null etc/systemd/system/<unit>`).

## The root encrypts itself on the first boot

The image's initramfs encrypts the root in place on the first boot when `/boot/efi/omarchy/install.conf` is absent or says `encrypt=1`. For an unencrypted install write `format=1`, `encrypt=0` and `lane=edge` (one per line) into that file. `tools/install-partitions.sh` does this.

## The pacman keyring is not initialised

`pacman -Sy` fails with "keyring is not writable". Run `pacman-key --init` and `pacman-key --populate` once. A small one-shot systemd unit that runs both while `/etc/pacman.d/gnupg/trustdb.gpg` is missing does it on the first boot.

## No Ethernet firmware

The image has no `linux-firmware`. The M6's built-in 10 GbE controller (Realtek RTL8127) then links at 5 Gb/s. Install `linux-firmware-realtek` (it provides `rtl_nic/rtl8127a-1.fw`) and the port links at 10 Gb/s. `ethtool` and `iperf3` are not in the image either.

## An idle lock screen with no way back in

If the user account has a locked password, nobody can log in again once the shell's idle lock engages. Set `idle.screensaver` and `idle.lock` to `0` in `~/.config/omarchy/shell.json`, or give the account a password.
