# Firmware

Some parts of the Mac need firmware from Apple: the GPU and the Wi-Fi and Bluetooth radio. We do not distribute any firmware, and nothing in this repository or in the kernel fork contains any.

You have to supply your own firmware, taken from your own Mac. The Linux kernel looks for it in the usual firmware search path, `/lib/firmware`, in files under `apple/`. The drivers that load it are not in the public tree yet. When they are, this page will list the exact file names.

The built-in Ethernet needs a different file. It is an ordinary public firmware file (`rtl_nic/rtl8127a-1.fw`, from `linux-firmware`). See [image-notes.md](image-notes.md).
