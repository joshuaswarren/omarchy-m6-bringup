#!/usr/bin/env python3
"""Split a packaged M6 payload (m1n1 | Image.gz | dtb | initramfs.cpio.gz | chosen.bootargs=...\\n | NUL*4) into parts.

  python3 split-payload.py PAYLOAD.macho OUTDIR
Prints sha256 of each part (Image is the gunzipped kernel). Stdlib only.
"""
import gzip
import hashlib
import re
import struct
import sys
from pathlib import Path

data = Path(sys.argv[1]).read_bytes()
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
args_at = data.rindex(b"chosen.bootargs=")
fdt_at = None
for m in re.finditer(b"\xd0\x0d\xfe\xed", data[:args_at]):
    total = struct.unpack_from(">I", data, m.start() + 4)[0]
    if 0 < total < 0x200000 and data[m.start() + 8:m.start() + 12] and m.start() > 0x100000:
        fdt_at = m.start()
        break
if fdt_at is None:
    raise SystemExit("no dtb found")
fdt_len = struct.unpack_from(">I", data, fdt_at + 4)[0]
gz_at = None
for m in re.finditer(b"\x1f\x8b\x08", data[:fdt_at]):
    try:
        d = gzip.GzipFile(fileobj=__import__("io").BytesIO(data[m.start():fdt_at])).read(64)
    except Exception:
        continue
    if d[0x38:0x3c] == b"ARM\x64":
        gz_at = m.start()
        break
if gz_at is None:
    raise SystemExit("no Image.gz found")
parts = {
    "Image.gz": data[gz_at:fdt_at],
    "board.dtb": data[fdt_at:fdt_at + fdt_len],
    "initramfs.cpio.gz": data[fdt_at + fdt_len:args_at],
    "bootargs.txt": data[args_at + len(b"chosen.bootargs="):data.index(b"\n", args_at)] + b"\n",
}
parts["Image"] = gzip.decompress(parts["Image.gz"]) if True else b""
for name, blob in parts.items():
    (out / name).write_bytes(blob)
    print(f"{hashlib.sha256(blob).hexdigest()}  {len(blob):>10}  {name}")
print("m1n1 part: bytes 0 ..", gz_at)
