#!/usr/bin/env python3
"""Extract the rootfs from an LG HB 8000 firmware ROM."""

import struct
import subprocess
import sys
import os

SH_ENTRY_SIZE = 40
SEC_UTDROOTFS = 28

def read_section_header(rom, e_shoff, idx):
    off = e_shoff + idx * SH_ENTRY_SIZE
    sh = rom[off:off + SH_ENTRY_SIZE]
    return {
        'sh_offset': struct.unpack_from('<I', sh, 16)[0],
        'sh_size': struct.unpack_from('<I', sh, 20)[0],
    }

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <original_ROM> <work_dir>")
        sys.exit(1)

    rom_path = sys.argv[1]
    work_dir = sys.argv[2]

    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(os.path.join(work_dir, "rootfs_full"), exist_ok=True)

    print(f"Loading ROM: {rom_path}")
    with open(rom_path, 'rb') as f:
        rom = f.read()

    e_shoff = struct.unpack_from('<I', rom, 32)[0]
    sh = read_section_header(rom, e_shoff, SEC_UTDROOTFS)

    xz_path = os.path.join(work_dir, "rootfs.tar.xz")
    print(f"Extracting UTDrootfs section ({sh['sh_size']} bytes) to {xz_path}")
    with open(xz_path, 'wb') as f:
        f.write(rom[sh['sh_offset']:sh['sh_offset'] + sh['sh_size']])

    print(f"Decompressing XZ...")
    tar_path = os.path.join(work_dir, "rootfs.tar")
    subprocess.run(["xz", "-d", "-k", "-f", xz_path], check=True)

    rootfs_dir = os.path.join(work_dir, "rootfs_full")
    print(f"Extracting tar to {rootfs_dir}")
    subprocess.run(["tar", "-xf", tar_path, "-C", rootfs_dir], check=True)

    print("Done! Rootfs extracted to", rootfs_dir)

if __name__ == '__main__':
    main()
