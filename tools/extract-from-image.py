#!/usr/bin/env python3
"""Pull the kernel, initramfs and board device tree out of an Omarchy Mac image zip, for compose-boot.py.

  python3 extract-from-image.py IMAGE.zip OUTDIR [--compat apple,j873g]

Writes OUTDIR/Image (raw arm64 Image from the UKI .linux), OUTDIR/initramfs.cpio (UKI .initrd), OUTDIR/cmdline.txt
(UKI .cmdline), and OUTDIR/<name>.dtb for the device tree in esp/m1n1/boot.bin whose root compatible list has --compat.
Exit 2 and no dtb file when no tree in the image carries that compatible value. Stdlib only.
"""
import argparse
import hashlib
import struct
import sys
import zipfile
from pathlib import Path


def pe_sections(data: bytes) -> dict:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + optional
    out = {}
    for i in range(count):
        o = table + 40 * i
        name = data[o:o + 8].rstrip(b"\0").decode()
        vsize, _, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
        out[name] = data[rawptr:rawptr + min(vsize, rawsize)]
    return out


def fdt_info(dtb: bytes):
    magic, total, off_struct, off_strings = struct.unpack_from(">IIII", dtb, 0)
    if magic != 0xD00DFEED:
        return None
    pos, depth, compat, model = off_struct, 0, [], None
    while pos < len(dtb):
        (token,) = struct.unpack_from(">I", dtb, pos)
        pos += 4
        if token == 1:
            pos = (dtb.index(b"\0", pos) + 4) & ~3
            depth += 1
        elif token == 2:
            depth -= 1
        elif token == 3:
            length, nameoff = struct.unpack_from(">II", dtb, pos)
            pos += 8
            data = dtb[pos:pos + length]
            pos = (pos + length + 3) & ~3
            if depth == 1:
                name = dtb[off_strings + nameoff:dtb.index(b"\0", off_strings + nameoff)].decode()
                if name == "compatible":
                    compat = [s.decode() for s in data.split(b"\0") if s]
                if name == "model":
                    model = data.rstrip(b"\0").decode()
        elif token == 9:
            break
    return total, compat, model


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--compat", default="apple,j873g")
    a = ap.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(a.zip)

    sections = pe_sections(z.read("esp/EFI/Linux/omarchy_linux-aurora.efi"))
    for name, dest in ((".linux", "Image"), (".initrd", "initramfs.cpio"), (".cmdline", "cmdline.txt")):
        blob = sections[name].rstrip(b"\0") if name == ".cmdline" else sections[name]
        (a.outdir / dest).write_bytes(blob)
        print(f"{dest}: {len(blob)} bytes sha256 {hashlib.sha256(blob).hexdigest()}")
    image = sections[".linux"]
    print("Image header: magic", image[56:60], "image_size", struct.unpack_from("<Q", image, 16)[0])

    boot = z.read("esp/m1n1/boot.bin")
    found, offset = [], 0
    while True:
        offset = boot.find(b"\xd0\x0d\xfe\xed", offset)
        if offset < 0:
            break
        info = fdt_info(boot[offset:offset + 4 * 1024 * 1024])
        if info and offset + info[0] <= len(boot) and info[1]:
            found.append((offset, info))
        offset += 4
    print(f"device trees in esp/m1n1/boot.bin: {len(found)}")
    for off, (total, compat, model) in found:
        if "apple,j873" in compat or a.compat in compat:
            print(f"  {off:#x} size {total} compatible {compat} model {model}")
    for off, (total, compat, _model) in found:
        if a.compat in compat:
            path = a.outdir / "board.dtb"
            path.write_bytes(boot[off:off + total])
            print(f"dtb: {path} sha256 {hashlib.sha256(boot[off:off + total]).hexdigest()}")
            return 0
    print(f"NO device tree with compatible {a.compat} in this image", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
