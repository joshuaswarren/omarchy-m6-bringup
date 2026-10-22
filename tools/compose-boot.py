#!/usr/bin/env python3
"""Compose the M6 boot object: raw m1n1 + kernel + device tree + initramfs + chosen variables.

Payload layout, in this order:
  m1n1.bin (padded to _payload_start) | Image.gz | dtb | initramfs.cpio.gz | "chosen.bootargs=...\\n" | 4 NUL bytes

Refuses a device tree whose root compatible list lacks the board value that m1n1 matches (apple,j873g).
Stdlib only.
"""
import argparse
import gzip
import hashlib
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

BOARD_COMPAT = "apple,j873g"
ARM64_MAGIC = b"ARM\x64"


def fdt_root_compatible(dtb: bytes) -> list[str]:
    magic, _total, off_struct, off_strings = struct.unpack_from(">IIII", dtb, 0)
    if magic != 0xD00DFEED:
        raise SystemExit("dtb: bad magic")
    pos = off_struct
    depth = 0
    while True:
        (token,) = struct.unpack_from(">I", dtb, pos)
        pos += 4
        if token == 1:
            end = dtb.index(b"\0", pos)
            pos = (end + 4) & ~3
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
                    return [s.decode() for s in data.split(b"\0") if s]
        elif token == 4:
            continue
        elif token == 9:
            return []
        else:
            raise SystemExit(f"dtb: bad token {token:#x}")


def macho_capacity(native: bytes) -> int:
    if struct.unpack_from("<I", native)[0] != 0xFEEDFACF:
        raise SystemExit("macho: bad magic")
    offset, caps = 32, []
    for _ in range(struct.unpack_from("<I", native, 16)[0]):
        command, size = struct.unpack_from("<II", native, offset)
        if command == 0x19 and native[offset + 8:offset + 24].rstrip(b"\0") == b"PYLD":
            vsize, file_offset, file_size = struct.unpack_from("<QQQ", native, offset + 32)
            if file_offset != len(native):
                raise SystemExit("macho: PYLD does not start at the end of the file")
            caps.append(min(vsize, file_size))
        offset += size
    if len(caps) != 1:
        raise SystemExit("macho: need exactly one PYLD segment")
    return caps[0]


def gz_bytes(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def check_gzip(data: bytes, what: str) -> None:
    try:
        zlib.decompressobj(31).decompress(data)
    except zlib.error as exc:
        raise SystemExit(f"{what}: gzip stream is bad ({exc})") from exc


def payload_start(elf: Path) -> int:
    out = subprocess.run(["nm", str(elf)], check=True, capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == "_payload_start":
            return int(parts[0], 16)
    raise SystemExit("nm: _payload_start not found")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m1n1", type=Path, help="raw build/m1n1.bin (boot object for kmutil)")
    ap.add_argument("--elf", type=Path, help="build/m1n1-raw.elf (for _payload_start; with --m1n1)")
    ap.add_argument("--macho", type=Path, help="build/m1n1.macho (for chainload.py; T8152 chainload needs a Mach-O)")
    ap.add_argument("--kernel", type=Path, required=True, help="Image or Image.gz")
    ap.add_argument("--dtb", type=Path, required=True)
    ap.add_argument("--initramfs", type=Path, required=True, help="cpio, gzip or plain")
    ap.add_argument("--bootargs", type=Path, required=True, help="one line, no chosen.bootargs= prefix")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--compat", default=BOARD_COMPAT)
    a = ap.parse_args()

    if bool(a.macho) == bool(a.m1n1):
        raise SystemExit("give exactly one of --macho or --m1n1 (with --elf)")
    capacity = None
    if a.macho:
        m1n1 = a.macho.read_bytes()
        start = len(m1n1)
        capacity = macho_capacity(m1n1)
    else:
        if not a.elf:
            raise SystemExit("--m1n1 needs --elf")
        m1n1 = a.m1n1.read_bytes()
        start = payload_start(a.elf)
        if len(m1n1) != start:
            raise SystemExit(f"m1n1.bin is {len(m1n1)} bytes, _payload_start is {start}: not the raw image of this ELF")

    dtb = a.dtb.read_bytes()
    compat = fdt_root_compatible(dtb)
    if a.compat not in compat:
        raise SystemExit(f"dtb: root compatible {compat} lacks {a.compat}; m1n1 rejects this device tree")

    kernel = a.kernel.read_bytes()
    if kernel[:2] == b"\x1f\x8b":
        check_gzip(kernel, "kernel")
        image = zlib.decompressobj(31).decompress(kernel)
    else:
        image = kernel
        kernel = gz_bytes(image)
    if image[56:60] != ARM64_MAGIC:
        raise SystemExit("kernel: no arm64 Image magic at offset 56")
    image_size = struct.unpack_from("<Q", image, 16)[0]

    initrd = a.initramfs.read_bytes()
    if initrd[:2] == b"\x1f\x8b":
        check_gzip(initrd, "initramfs")
    elif initrd[:6] != b"070701":
        raise SystemExit("initramfs: neither gzip nor newc cpio")

    line = a.bootargs.read_text().strip()
    if "\n" in line or not line:
        raise SystemExit("bootargs: need exactly one non-empty line")
    variable = b"chosen.bootargs=" + line.encode("ascii") + b"\n"

    blob = m1n1 + kernel + dtb + initrd + variable + b"\0\0\0\0"
    if capacity is not None and len(blob) - start > capacity:
        raise SystemExit(f"payload {len(blob) - start} bytes exceeds the Mach-O PYLD capacity {capacity}")
    a.out.write_bytes(blob)
    manifest = {
        "out": a.out.name,
        "size": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "m1n1_sha256": hashlib.sha256(m1n1).hexdigest(),
        "payload_start": start,
        "kernel_gz_sha256": hashlib.sha256(kernel).hexdigest(),
        "kernel_image_size": image_size,
        "dtb_sha256": hashlib.sha256(dtb).hexdigest(),
        "dtb_compatible": compat,
        "initramfs_sha256": hashlib.sha256(initrd).hexdigest(),
        "bootargs": line,
        "payload_bytes": len(blob) - start,
    }
    a.out.with_suffix(a.out.suffix + ".json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    sys.exit(main())
