# Put the boot payload together

The boot loader (m1n1) can carry a kernel with it. A boot object is the loader binary followed by the kernel, the device tree, the initramfs and the kernel command line. `tools/compose-boot.py` builds it.

## Layout

```
m1n1 (padded up to the start of the payload area)
Image.gz               gzip-compressed kernel Image
board.dtb              device tree
initramfs.cpio.gz      initramfs
chosen.bootargs=...    one line of kernel command line, then a newline
0 0 0 0                four zero bytes
```

This is the m1n1 payload convention. The loader reads the command line from the `chosen.bootargs` variable.

## Compose

Two forms of the same payload:

```sh
# Raw boot object, for kmutil (see install.md).
python3 tools/compose-boot.py \
    --m1n1 m1n1.bin --elf m1n1-raw.elf \
    --kernel Image.gz --dtb board.dtb --initramfs initramfs.cpio.gz \
    --bootargs bootargs.txt --out boot.bin

# Mach-O, for chainloading from a second computer with the m1n1 proxy client.
# The M6 loader needs a Mach-O for a chainload.
python3 tools/compose-boot.py \
    --macho m1n1.macho \
    --kernel Image.gz --dtb board.dtb --initramfs initramfs.cpio.gz \
    --bootargs bootargs.txt --out payload.macho
```

`--kernel` takes a raw `Image` or an `Image.gz`. `--bootargs` is a file with one line and without the `chosen.bootargs=` prefix. The tool writes `<out>.json` next to the output with the size and the SHA-256 of every part.

The tool refuses a device tree whose root `compatible` list does not contain `apple,j873g`, the board value the loader matches.

## Check a payload

```sh
python3 tools/split-payload.py payload.macho parts/
```

This writes the kernel, the device tree, the initramfs and the command line to `parts/` and prints the SHA-256 of each. Use it to prove that two payloads differ only where you expect.

## Get an initramfs and a command line from an Omarchy Mac image

```sh
python3 tools/extract-from-image.py IMAGE.zip out/ --compat apple,j873g
```

This reads the unified kernel image in the zip and writes `Image`, `initramfs.cpio` and `cmdline.txt`. It also writes the device tree from the image's boot object that carries the compatible string you pass; it exits with status 2 and writes no device tree when the image has none for that board. For the M6 you need your own kernel and device tree, so use the extracted initramfs and command line as a starting point only.

## The loader

You need an m1n1 build with M6 support. The public [aurora-silicon/m1n1](https://github.com/aurora-silicon/m1n1) repository has basic M6 support on its `aurora-wip` branch. The loader we used for the results in the README has more changes that are not published yet.
