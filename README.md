# LG HB 8000 Soundbar - Custom Firmware

Modified firmware for the LG HB 8000 (BH7430PB) soundbar with persistent root telnet access and a custom VFD display Easter egg.

## What's in the mod

| Change | Description |
|--------|-------------|
| **Telnet root shell** | Persistent telnetd starts on boot via inetd — connect with `telnet <soundbar-ip>` for a root shell |
| **OWO display** | The VFD front panel shows `OWO` instead of `ARC` when in soundbar/ARC mode |

The device runs Linux 2.6.35 on a MediaTek MT8550 (ARM Cortex-A9). The firmware is an ELF container wrapping an XZ-compressed rootfs and several data sections.

## Flashing the pre-built ROM

1. Download `LG_HB_8000M80.ROM` from the [Releases](../../releases) page
2. Format a USB drive as FAT32
3. Create a folder `UPG_ALL` on the root of the drive
4. Copy `LG_HB_8000M80.ROM` into `UPG_ALL/`
5. Insert the USB drive into the soundbar's USB port — the update starts automatically
6. Wait for the display to show completion (do **not** unplug power during update)
7. After reboot, connect via `telnet <soundbar-ip>` (default port 23)

## Using telnet

Once flashed, telnetd starts ~15 seconds after boot:

```
telnet 192.168.178.30
```

You get a root shell (`/bin/sh`). The soundbar must be on your network (wired or wireless).

## Building from source

If you want to build the ROM yourself from the original firmware:

### Prerequisites

- Python 3.6+
- `xz` command-line tool (with LZMA2 support)
- `tar` with GNU format support (`gnutar` on macOS)
- The original `LG_HB_8000M80.ROM` firmware file

### Steps

```bash
# 1. Extract the rootfs from the original ROM
python3 tools/extract_rootfs.py /path/to/original/LG_HB_8000M80.ROM work/

# 2. Apply patches to the extracted rootfs
python3 patches/apply_patches.py work/

# 3. Repack the rootfs into XZ
cd work/rootfs_full
tar --format=gnutar -cf ../rootfs_modified.tar .
xz -z --lzma2=dict=256KiB --check=crc64 -f ../rootfs_modified.tar
cd ../..

# 4. Build the final ROM
python3 tools/build_rom.py /path/to/original/LG_HB_8000M80.ROM work/rootfs_modified.tar.xz output/LG_HB_8000M80.ROM
```

The build bumps the firmware version byte from `0x48` to `0x90` so the device accepts the update, and recalculates the XOR checksum in the RAWDATA section.

## Technical details

### Hardware

- **Model:** LG HB 8000 / BH7430PB
- **SoC:** MediaTek MT8550 (ARM Cortex-A9)
- **OS:** Linux 2.6.35, BusyBox + bash 3.2.51
- **Storage:** eMMC with 23 partitions, rootfs at partition 23

### ROM format

The firmware ROM is an ELF32 container with these payload sections:

| Section | Description |
|---------|-------------|
| RAWDATA | Main data blob containing version info and XOR checksum |
| UTDrootfs | XZ-compressed GNU tar of the root filesystem |
| TARDATA | Additional tar data (kept unchanged) |
| BZ2DATA | BZ2-compressed data (kept unchanged) |
| UPGDATA | Upgrade metadata (kept unchanged) |
| FILESIZE | Size marker section |

### Patches applied

**Telnet persistence** — `dbus-start.sh` is replaced with:

```sh
#!/bin/sh
(sleep 15 && echo "telnet stream tcp nowait root /usr/sbin/telnetd telnetd -E /bin/sh" > /tmp/inetd.conf && /usr/sbin/inetd /tmp/inetd.conf) &
```

This starts inetd with a telnet service 15 seconds after boot. The delay is needed because telnetd (GNU inetutils 1.4.2) requires inetd as a super-server — it cannot listen standalone.

**OWO display** — Two instances of `ARC` in the VFD string table inside `bdpprog` are patched to `OWO`:

| Offset | Original | Patched |
|--------|----------|---------|
| `0xF27CAE` | `   ARC   ` | `   OWO   ` |
| `0xF27EAE` | `   ARC  ` | `   OWO  ` |

### Initial access (Shellshock)

The original firmware's bash 3.2.51 is vulnerable to Shellshock (CVE-2014-6271). Initial root access can be obtained by injecting a payload via DHCP option strings — the device's DHCP client passes options through bash environment variables without sanitization. This mod makes that initial exploit unnecessary by providing persistent telnet access.

## Disclaimer

This is provided for educational and personal use. Modifying firmware may void your warranty. The authors are not responsible for bricked devices. Always keep a backup of your original firmware.

## License

MIT
