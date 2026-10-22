# Install to the internal NVMe drive

This is what we do on our Mac mini. It is experimental. Read all of it before you start, and keep a second computer next to the Mac.

macOS stays on the machine. The steps add three partitions after the existing containers and change the boot object of one small stub volume. They do not touch the macOS volume.

## What you need

- The Mac mini with the M6 chip, running macOS, with enough free space: about 500 MiB for the EFI partition, 2 GiB for the boot partition, and the root partition you want (the image is about 13 GB and the root grows after the first boot).
- A second computer on the same network, with Python 3.9 or newer.
- An Omarchy Mac image zip. It holds `esp/`, `boot.img` and `root.img`. See the [Omarchy Mac](https://github.com/omacom/omarchy-mac) project.
- A stub volume, created by the Omarchy Mac installer, and the owner password of the Mac.
- A boot object for the M6: see [boot-payload.md](boot-payload.md).
- A root image whose filesystem UUID you changed: see [image-notes.md](image-notes.md), "Fixed filesystem UUIDs".

## 1. Start the image server on the second computer

```sh
printf '%s  root.img\n%s  boot.img\n' "$(sha256sum < root.img | cut -d' ' -f1)" \
    "$(unzip -p IMAGE.zip boot.img | sha256sum | cut -d' ' -f1)" > SHA256SUMS
python3 tools/image-server.py --zip IMAGE.zip --boot-bin boot.bin \
    --sums SHA256SUMS --root-file root.img --allow <network of the Mac>/24
```

The server prints a one-time token. Every URL starts with it: `http://<second computer>:8766/<token>/...`. Only addresses inside `--allow` can connect. `--root-file` serves your changed root image instead of the one in the zip. `SHA256SUMS` must contain the SHA-256 of the root image you serve, not of the one in the zip.

## 2. Create the partitions and write the image

Start the Mac in macOS or in the recovery Terminal. In Terminal, with `S` set to the server URL including the token:

```sh
S=http://<second computer>:8766/<token>
curl -fsS $S/install-partitions.sh -o /tmp/install-partitions.sh
SERVER=$S AFTER=disk0s3 bash /tmp/install-partitions.sh --dry-run
```

`AFTER` is the APFS container of the stub volume (see `diskutil list`). The dry run prints the partition order, the free space after `AFTER`, and every command. It changes nothing. When it looks right:

```sh
SERVER=$S AFTER=disk0s3 REVIEWED=disk0s3 bash /tmp/install-partitions.sh --go
```

The script adds the EFI, boot and root partitions, writes `boot.img` and `root.img`, checks the SHA-256 of each stream and of a read-back from the disk, unpacks `esp.tar` into the EFI partition, and writes `omarchy/install.conf` with `encrypt=0` (see [image-notes.md](image-notes.md): without it the image encrypts the root in place on the first boot).

## 3. Replace the boot object

Start the stub volume's own recoveryOS: shut down, then press and hold the power button until the startup options appear, and choose the stub volume. In Terminal, with `S` set as above:

```sh
curl -fsS $S/enrol-boot-object.sh -o /tmp/enrol-boot-object.sh
SERVER=$S WANT_SHA=<sha256 of boot.bin> VGID=<volume group UUID> SYSTEM_DIR=/Volumes/<stub> \
    bash /tmp/enrol-boot-object.sh --check
```

`VGID` comes from `bputil -d`. The check confirms that this recovery is the stub's own, that the object has the hash you expect, and prints the `kmutil` command it would run. Then run the same line with `--go`. It asks for the owner password twice. To go back, run it again with the previous boot object.

## 4. Restart

Restart the Mac. Do not shut it down. The Mac starts the new boot object. After the first boot, grow the root filesystem:

```sh
sudo btrfs filesystem resize max /
```

## Limits

- Starting the Linux boot object on its own is not set up yet. Our flow chainloads the payload from a second computer.
- The startup options screen does not always appear. We needed several tries with the power button held.
- Nothing here has a rollback for a wrong partition table. Read the dry run.
