# Omarchy on the Mac mini (M6): experimental bring-up

This repository holds the instructions and the helper tools for getting Omarchy to run on the Apple Mac mini with the M6 chip. It is experimental and unfinished. It is not an installer and it is not ready for daily use.

The Linux kernel changes live in a separate fork, branch `m6-bringup` of [joshuaswarren/linux-aurora](https://github.com/joshuaswarren/linux-aurora). This repository covers everything around the kernel: how to build it, how to put a boot payload together, how to install to the internal NVMe drive, and what works today.

## Questions people ask

**Does this wipe macOS?** No. macOS stays installed next to Linux, and the boot setup needs it. The steps below add partitions after the macOS containers and change the boot object of one small volume. They do not touch your macOS volume.

**Which machines does this cover?** Only the Mac mini with the M6 chip. For M1, M2 and M3 machines, use the [Omarchy Mac](https://github.com/omacom/omarchy-mac) project.

**Can I use it as my daily machine?** No. See the status table. There is no GPU driver in the public tree, no native display driver, no Wi-Fi and no audio yet.

## What works today

This is what we see on our own Mac mini. Several rows depend on code that is not in the public fork yet; the last column says which.

| Part | Status | In the public fork |
|---|---|---|
| CPU | All 12 cores start. Frequency scaling works. | partly (loader change for CPU start only) |
| Internal NVMe | Install and boot from the internal drive work. | partly (NVMe driver change only) |
| Ethernet | The built-in 10 GbE port links at 10 Gb/s. iperf3 to another 10 GbE machine gave about 8.0 Gb/s sending and 9.1 Gb/s receiving. | no |
| USB | Front ports (USB 2 speeds) and rear ports work. USB 3 speeds on the front hub are not done. | partly (USB 2 PHY driver, hub quirk, power domains) |
| GPU | A kernel driver and Mesa work: OpenGL, Vulkan and compute smoke tests pass, and the Hyprland desktop renders on the GPU. | no |
| Display | The 1280x720 framebuffer from the boot loader. There is no native display driver. | no |
| Wi-Fi and Bluetooth | The radio's firmware starts. The driver is not finished. | no |
| Audio | Not done. | no |
| Sensors, fan, clock, power button | Temperatures, fan speed, the real-time clock and the power button work. | no |
| Power off | The Mac restarts instead of powering off. | no |

## What is in the public kernel fork

The branch `m6-bringup` is built on the public `omacom/linux-aurora` tree (branch `integration/aurora`) and adds six changes:

- a pin controller compatible string for the M6
- the register layout of the M6 SART
- NVMe controller changes for the M6
- power domains for the M6 power state director
- a USB 2 PHY driver for the fixed host ports
- a USB hub quirk for the front-port hub

It does not boot the machine by itself yet. These parts are not in the public tree yet: the board device tree, the memory management, PCIe and USB controller changes, and the GPU, display and Wi-Fi drivers. We will add pieces as they are ready.

## What is in this repository

| Path | What it is |
|---|---|
| [docs/build-kernel.md](docs/build-kernel.md) | Cross-build the kernel from the fork. |
| [docs/boot-payload.md](docs/boot-payload.md) | Put the loader, kernel, device tree and initramfs into one boot object. |
| [docs/install.md](docs/install.md) | Install to the internal NVMe drive. |
| [docs/boot-args.md](docs/boot-args.md) | The kernel command line we use, argument by argument. |
| [docs/image-notes.md](docs/image-notes.md) | Problems we found in Omarchy Mac images and how we fix them. |
| [docs/firmware.md](docs/firmware.md) | Firmware: what you need to supply. |
| `tools/compose-boot.py` | Build the boot object. |
| `tools/split-payload.py` | Take a boot object apart again and print the hash of every part. |
| `tools/extract-from-image.py` | Pull the kernel, initramfs and command line out of an Omarchy Mac image. |
| `tools/image-server.py` | Serve an image to the Mac while it runs recovery. |
| `tools/install-partitions.sh` | Create the three partitions and write the image (macOS or recovery Terminal). |
| `tools/enrol-boot-object.sh` | Replace the boot object of the stub volume (recovery Terminal). |

## Known limits

- Everything here is tested on one machine. Other M6 Mac minis may differ.
- The boot loader we use has more changes than the ones we publish. The public `aurora-silicon/m1n1` repository has basic M6 support on its `aurora-wip` branch. Our CPU start change is on the `m6-bringup` branch of [joshuaswarren/m1n1](https://github.com/joshuaswarren/m1n1). It builds on `aurora-wip`. We built it there, but we have not booted that exact build. The rest of our loader changes come later.
- Power off from Linux restarts the Mac. If you shut the Mac down from macOS, someone has to press the power button to start it again.
- At the time of writing our boot flow starts Linux from a second computer over the USB cable. Starting Linux on its own is not set up yet.
- You use these tools at your own risk. A wrong boot object can leave the Linux boot volume unbootable. Keep macOS reachable.

## License

The tools in this repository are MIT licensed. See [LICENSE](LICENSE).
