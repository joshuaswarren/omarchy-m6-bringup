# Build the kernel

The kernel fork is [joshuaswarren/linux-aurora](https://github.com/joshuaswarren/linux-aurora), branch `m6-bringup`. It is the public `omacom/linux-aurora` tree (branch `integration/aurora`) plus six M6 changes. See the README for what those changes are and what is not in the tree yet.

## Get the source

```sh
git clone --branch m6-bringup https://github.com/joshuaswarren/linux-aurora.git
cd linux-aurora
```

The history is large. Add `--filter=blob:none` to the clone if you want a quick start.

## Configure

Start from the configuration of a kernel that already runs Omarchy on Apple Silicon, for example the config of the installed `linux-aurora` package, then bring it up to date:

```sh
cp /path/to/known-good.config .config
make ARCH=arm64 LLVM=1 olddefconfig
```

The M6 changes need these options (the new ones are marked):

| Option | Purpose |
|---|---|
| `CONFIG_ARCH_APPLE=y` | Apple Silicon support. |
| `CONFIG_BLK_DEV_NVME=m`, `CONFIG_NVME_APPLE=m` | Internal NVMe drive. |
| `CONFIG_APPLE_SART=y` | Address filter in front of the NVMe controller. |
| `CONFIG_APPLE_PMGR_PSD=y` (new) | Power domains for the power state director. |
| `CONFIG_PHY_APPLE_T8152_USB2=y` (new) | USB 2 PHY of the fixed host ports. |
| `CONFIG_APPLE_TUNABLE=y` | Used by the USB 2 PHY driver. |
| `CONFIG_PINCTRL_APPLE_GPIO=y` | GPIO. |

The tree contains Rust drivers. Turn `CONFIG_RUST` off unless your `rustc` and `bindgen` match the versions in `Documentation/process/changes.rst`.

## Build

```sh
make ARCH=arm64 LLVM=1 -j"$(nproc)" Image modules dtbs
make ARCH=arm64 LLVM=1 INSTALL_MOD_PATH=/tmp/modroot modules_install
```

`Image` is the kernel for the boot object (see [boot-payload.md](boot-payload.md)). The modules go into the root filesystem under `/usr/lib/modules/<release>`. Run `depmod` on the root afterwards.

## What we compiled

We compiled the six changed source files with GCC 12.2 (`aarch64-linux-gnu`) on a defconfig with the options above enabled: `drivers/nvme/host/apple.c`, `drivers/soc/apple/sart.c`, `drivers/pmdomain/apple/pmgr-psd.c`, `drivers/phy/apple/usb2-t8152.c`, `drivers/usb/core/hub.c` and `drivers/pinctrl/pinctrl-apple-gpio.c`. All six compiled without errors. We have not booted this exact public tree on the Mac mini.
