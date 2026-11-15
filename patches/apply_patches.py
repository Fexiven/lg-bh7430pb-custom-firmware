#!/usr/bin/env python3
"""Apply all patches to an extracted LG HB 8000 rootfs."""

import os
import stat
import sys

def patch_owo(work_dir):
    """Patch ARC -> OWO in the VFD string table of bdpprog."""
    bdpprog = os.path.join(work_dir, "rootfs_full/mnt/rootfs_normal/usr/local/bin/bdpprog")

    patches = [
        (0xF27CAE, b"   ARC   \x00", b"   OWO   \x00"),
        (0xF27EAE, b"   ARC  \x00",  b"   OWO  \x00"),
    ]

    print("Patching bdpprog: ARC -> OWO")
    with open(bdpprog, 'r+b') as f:
        for offset, original, replacement in patches:
            f.seek(offset)
            actual = f.read(len(original))
            if actual == replacement:
                print(f"  0x{offset:06x}: already patched")
                continue
            if actual != original:
                print(f"  0x{offset:06x}: UNEXPECTED content: {actual!r}")
                print(f"  Expected: {original!r}")
                sys.exit(1)
            f.seek(offset)
            f.write(replacement)
            print(f"  0x{offset:06x}: patched")

def patch_telnet(work_dir):
    """Replace dbus-start.sh with telnet persistence launcher."""
    rootfs = os.path.join(work_dir, "rootfs_full")

    target = os.path.join(rootfs, "mnt/rootfs_normal/usr/local/etc/dbus-start.sh")
    if not os.path.exists(target):
        target = os.path.join(rootfs, "usr/local/etc/dbus-start.sh")

    if not os.path.exists(target):
        for root, dirs, files in os.walk(rootfs):
            if "dbus-start.sh" in files:
                target = os.path.join(root, "dbus-start.sh")
                break
        else:
            print("ERROR: dbus-start.sh not found in rootfs")
            sys.exit(1)

    print(f"Patching telnet persistence: {os.path.relpath(target, work_dir)}")

    content = '#!/bin/sh\n(sleep 15 && echo "telnet stream tcp nowait root /usr/sbin/telnetd telnetd -E /bin/sh" > /tmp/inetd.conf && /usr/sbin/inetd /tmp/inetd.conf) &\n'

    with open(target, 'w') as f:
        f.write(content)

    os.chmod(target, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    print("  done")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <work_dir>")
        print("  work_dir should contain rootfs_full/ from extract_rootfs.py")
        sys.exit(1)

    work_dir = sys.argv[1]
    rootfs = os.path.join(work_dir, "rootfs_full")

    if not os.path.isdir(rootfs):
        print(f"ERROR: {rootfs} not found. Run extract_rootfs.py first.")
        sys.exit(1)

    patch_owo(work_dir)
    patch_telnet(work_dir)
    print("\nAll patches applied.")

if __name__ == '__main__':
    main()
