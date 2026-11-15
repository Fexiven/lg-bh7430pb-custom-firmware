#!/usr/bin/env python3
"""Build a modified LG HB 8000 firmware ROM from original + modified rootfs XZ."""

import struct
import sys
import os

SEC_RAWDATA = 27
SEC_UTDROOTFS = 28
SEC_TARDATA = 29
SEC_BZ2DATA = 30
SEC_UPGDATA = 31
SEC_FILESIZE = 32

SH_ENTRY_SIZE = 40

VERSION_BYTE_OFF = 6130084
XORS_VALUE_OFF = 6130148

NEW_VERSION_BYTE = 0x90

def read_section_header(rom, e_shoff, idx):
    off = e_shoff + idx * SH_ENTRY_SIZE
    sh = rom[off:off + SH_ENTRY_SIZE]
    fields = ['sh_name', 'sh_type', 'sh_flags', 'sh_addr', 'sh_offset',
              'sh_size', 'sh_link', 'sh_info', 'sh_addralign', 'sh_entsize']
    return {fields[i]: struct.unpack_from('<I', sh, i * 4)[0] for i in range(10)}

def write_section_header(rom, e_shoff, idx, sh):
    off = e_shoff + idx * SH_ENTRY_SIZE
    fields = ['sh_name', 'sh_type', 'sh_flags', 'sh_addr', 'sh_offset',
              'sh_size', 'sh_link', 'sh_info', 'sh_addralign', 'sh_entsize']
    for i, name in enumerate(fields):
        struct.pack_into('<I', rom, off + i * 4, sh[name])

def xor_checksum(data):
    result = 0
    for i in range(0, len(data) - 3, 4):
        result ^= struct.unpack_from('<I', data, i)[0]
    return result

def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <original_ROM> <modified_rootfs.tar.xz> <output_ROM>")
        sys.exit(1)

    rom_path, xz_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

    print(f"Loading original ROM: {rom_path}")
    with open(rom_path, 'rb') as f:
        rom = bytearray(f.read())

    e_shoff = struct.unpack_from('<I', rom, 32)[0]
    e_shnum = struct.unpack_from('<H', rom, 48)[0]
    print(f"ELF: {e_shnum} sections, section headers at offset {e_shoff}")

    sections = {i: read_section_header(rom, e_shoff, i) for i in range(e_shnum)}

    print(f"Loading modified rootfs: {xz_path}")
    with open(xz_path, 'rb') as f:
        new_xz = f.read()
    print(f"New XZ: {len(new_xz)} bytes (original: {sections[SEC_UTDROOTFS]['sh_size']})")

    tardata = bytes(rom[sections[SEC_TARDATA]['sh_offset']:
                        sections[SEC_TARDATA]['sh_offset'] + sections[SEC_TARDATA]['sh_size']])
    bz2data = bytes(rom[sections[SEC_BZ2DATA]['sh_offset']:
                        sections[SEC_BZ2DATA]['sh_offset'] + sections[SEC_BZ2DATA]['sh_size']])
    upgdata = bytes(rom[sections[SEC_UPGDATA]['sh_offset']:
                        sections[SEC_UPGDATA]['sh_offset'] + sections[SEC_UPGDATA]['sh_size']])

    rawdata_sh = sections[SEC_RAWDATA]
    utd_start = rawdata_sh['sh_offset'] + rawdata_sh['sh_size']
    new_tardata_off = utd_start + len(new_xz)
    new_bz2data_off = new_tardata_off + sections[SEC_TARDATA]['sh_size']
    new_upgdata_off = new_bz2data_off + sections[SEC_BZ2DATA]['sh_size']
    new_total_size = new_upgdata_off + sections[SEC_UPGDATA]['sh_size']

    print(f"Building ROM ({new_total_size} bytes, was {len(rom)})...")
    new_rom = bytearray(rom[:utd_start])
    new_rom.extend(new_xz)
    new_rom.extend(tardata)
    new_rom.extend(bz2data)
    new_rom.extend(upgdata)
    assert len(new_rom) == new_total_size

    sections[SEC_UTDROOTFS]['sh_offset'] = utd_start
    sections[SEC_UTDROOTFS]['sh_size'] = len(new_xz)
    sections[SEC_TARDATA]['sh_offset'] = new_tardata_off
    sections[SEC_BZ2DATA]['sh_offset'] = new_bz2data_off
    sections[SEC_UPGDATA]['sh_offset'] = new_upgdata_off
    sections[SEC_FILESIZE]['sh_offset'] = new_total_size
    sections[SEC_FILESIZE]['sh_addralign'] = new_total_size

    for i in [SEC_UTDROOTFS, SEC_TARDATA, SEC_BZ2DATA, SEC_UPGDATA, SEC_FILESIZE]:
        write_section_header(new_rom, e_shoff, i, sections[i])

    struct.pack_into('<I', new_rom, 7, new_total_size)
    struct.pack_into('<I', new_rom, 11, new_total_size)

    raw_off = rawdata_sh['sh_offset']
    old_ver = new_rom[raw_off + VERSION_BYTE_OFF]
    new_rom[raw_off + VERSION_BYTE_OFF] = NEW_VERSION_BYTE
    old_srev = struct.unpack_from('<I', new_rom, raw_off + VERSION_BYTE_OFF)[0]
    struct.pack_into('<I', new_rom, raw_off + VERSION_BYTE_OFF, (old_srev & 0xFFFFFF00) | NEW_VERSION_BYTE)
    print(f"Version: 0x{old_ver:02x} -> 0x{NEW_VERSION_BYTE:02x}")

    struct.pack_into('<I', new_rom, raw_off + XORS_VALUE_OFF, 0)
    checksum = xor_checksum(bytes(new_rom[raw_off:raw_off + rawdata_sh['sh_size']]))
    struct.pack_into('<I', new_rom, raw_off + XORS_VALUE_OFF, checksum)
    print(f"XOR checksum: 0x{checksum:08x}")

    with open(out_path, 'wb') as f:
        f.write(new_rom)
    print(f"Written: {out_path} ({len(new_rom)} bytes)")

    # Verify
    verify_data = bytearray(new_rom[raw_off:raw_off + rawdata_sh['sh_size']])
    struct.pack_into('<I', verify_data, XORS_VALUE_OFF, 0)
    assert xor_checksum(bytes(verify_data)) == checksum, "Checksum verification failed!"
    sz1 = struct.unpack_from('<I', new_rom, 7)[0]
    sz2 = struct.unpack_from('<I', new_rom, 11)[0]
    assert sz1 == sz2 == len(new_rom), "Size field verification failed!"
    print("Verification passed.")

if __name__ == '__main__':
    main()
