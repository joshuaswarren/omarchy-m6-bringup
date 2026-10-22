#!/usr/bin/env python3
"""Serve an Omarchy Mac image to the Mac mini over HTTP while it runs recoveryOS or macOS.

  python3 image-server.py --zip IMAGE.zip --boot-bin boot.bin --sums SHA256SUMS --allow 192.0.2.0/24 [--root-file root.img]

Paths (every path starts with the one-time token that is printed at start):
  /<token>/boot.img      boot partition image, streamed out of the zip
  /<token>/root.img      root image, streamed out of the zip, or from --root-file
  /<token>/esp.tar       tar of the zip's esp/ tree, built on the fly
  /<token>/boot.bin      the boot object for kmutil (from --boot-bin)
  /<token>/SHA256SUMS    expected hashes (from --sums): lines "<sha256>  root.img" and "<sha256>  boot.img"
  /<token>/sizes         "<name> <bytes>" for boot.img and root.img
  /<token>/<script>      any of the scripts in this directory (install-partitions.sh, enrol-boot-object.sh)

Only addresses inside --allow connect. Nothing is written to disk. Stdlib only (Python 3.9+).
"""
import argparse
import http.server
import ipaddress
import secrets
import socketserver
import sys
import tarfile
import zipfile
from pathlib import Path

SCRIPTS = ("install-partitions.sh", "enrol-boot-object.sh")
CHUNK = 1 << 20


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def send_bytes(self, data: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with path.open("rb") as f:
            while chunk := f.read(CHUNK):
                self.wfile.write(chunk)

    def do_GET(self):
        cfg = self.server.cfg
        parts = self.path.lstrip("/").split("/", 1)
        if len(parts) != 2 or not secrets.compare_digest(parts[0], cfg.token):
            self.send_error(404)
            return
        if not any(ipaddress.ip_address(self.client_address[0]) in net for net in cfg.allow):
            self.send_error(403)
            return
        name = parts[1]
        if name == "boot.bin":
            self.send_file(cfg.boot_bin)
        elif name == "SHA256SUMS":
            self.send_file(cfg.sums)
        elif name == "sizes":
            self.send_bytes("".join(f"{k} {v}\n" for k, v in cfg.sizes.items()).encode())
        elif name in SCRIPTS:
            self.send_file(Path(__file__).resolve().parent / name)
        elif name == "root.img" and cfg.root_file:
            self.send_file(cfg.root_file)
        elif name in ("boot.img", "root.img"):
            with zipfile.ZipFile(cfg.zip) as z, z.open(name) as member:
                self.send_response(200)
                self.send_header("Content-Length", str(cfg.sizes[name]))
                self.end_headers()
                while chunk := member.read(CHUNK):
                    self.wfile.write(chunk)
        elif name == "esp.tar":
            self.send_response(200)
            self.end_headers()
            with zipfile.ZipFile(cfg.zip) as z, tarfile.open(fileobj=self.wfile, mode="w|") as tar:
                for info in z.infolist():
                    if info.filename.startswith("esp/") and not info.is_dir():
                        entry = tarfile.TarInfo(info.filename[4:])
                        entry.size = info.file_size
                        entry.mode = 0o644
                        with z.open(info) as f:
                            tar.addfile(entry, f)
        else:
            self.send_error(404)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, required=True, help="Omarchy Mac image zip (esp/, boot.img, root.img)")
    ap.add_argument("--boot-bin", type=Path, required=True)
    ap.add_argument("--sums", type=Path, required=True)
    ap.add_argument("--allow", action="append", required=True, help="client address or network (repeatable)")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--root-file", type=Path, default=None, help="serve root.img from this file instead of the zip")
    ap.add_argument("--token", default=None)
    cfg = ap.parse_args()
    cfg.allow = [ipaddress.ip_network(a, strict=False) for a in cfg.allow]
    cfg.token = cfg.token or secrets.token_urlsafe(12)
    with zipfile.ZipFile(cfg.zip) as z:
        cfg.sizes = {m: z.getinfo(m).file_size for m in ("boot.img", "root.img")}
    if cfg.root_file:
        cfg.sizes["root.img"] = cfg.root_file.stat().st_size
    print("sizes", cfg.sizes, flush=True)
    print(f"token {cfg.token}", flush=True)
    server = Server(("0.0.0.0", cfg.port), Handler)
    server.cfg = cfg
    server.serve_forever()


if __name__ == "__main__":
    main()
