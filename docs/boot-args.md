# Kernel command line

The command line of the boot object we test with:

```
console=tty0 loglevel=4 rw panic=0 idle=wfi arm64.nowfxt nokaslr apple_mailbox.ascwrap_v8_cpu_control=1 g_ncm.host_addr=02:00:00:06:00:01 g_ncm.dev_addr=02:00:00:06:00:02
```

Our initramfs mounts the root partition of the internal drive by device name, so the line has no `root=` argument. With the initramfs of an Omarchy Mac image you need one: `root=UUID=<filesystem UUID> rootflags=subvol=@ rootfstype=btrfs`, with the UUID you set (see [image-notes.md](image-notes.md), "Fixed filesystem UUIDs"). We have not booted that combination yet.

| Argument | Meaning |
|---|---|
| `console=tty0` | Kernel messages on the firmware framebuffer. |
| `loglevel=4` | Warnings and errors only. Use `7` while you debug. |
| `rw` | Mount the root read-write. |
| `panic=0` | Do not reboot after a panic, so the message stays on the screen. |
| `idle=wfi`, `arm64.nowfxt` | Kept from our first boots. |
| `nokaslr` | No kernel address randomisation. Easier to debug. |
| `apple_mailbox.ascwrap_v8_cpu_control=1` | A parameter of the mailbox driver for the M6. That driver change is not in the public fork yet, so the argument has no effect there. |
| `g_ncm.host_addr`, `g_ncm.dev_addr` | MAC addresses for a USB Ethernet gadget (CDC NCM) on the Mac's USB cable. It gives the Mac a network link to the second computer. Pick any locally administered addresses. |

Do not add `maxcpus=1`. Earlier builds used it. All 12 CPUs start without it.
