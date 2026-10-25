#!/usr/bin/env python3
"""Repack the LOS laurel_sprout (A/B, header v2) boot.img for the A-only CC9e abl.

What it changes, and why:
  * header v2 -> v1: the stock CC9e boot is v1 with DTBs appended to Image.gz;
    the A9 laurus abl is not known to read the v2 dtb section.
  * ramdisk fstabs (first_stage fstab.qcom + recovery.fstab): drop `slotselect`
    (the CC9e abl passes no androidboot.slot_suffix -> fs_mgr refuses the fstab)
    and `avb*` (abl passes no androidboot.vbmeta.* -> first-stage AVB would fail).
  * cmdline: add androidboot.force_normal_boot=1 (LOS boot is recovery-as-boot;
    without it first-stage init boots LOS recovery) and
    androidboot.vbmeta.device_state=unlocked. Omit force_normal_boot with
    --recovery to get an image for the `recovery` partition.
  * --debuggable PLAT_SEPOLICY_CIL: add AOSP's force_debuggable trio
    (force_debuggable, adb_debug.prop, userdebug_plat_sepolicy.cil) to the ramdisk
    root and first_stage_ramdisk/. On an unlocked device init then loads
    adb_debug.prop with top priority (ro.debuggable=1, ro.adb.secure=0, adb on), so
    adb works from early boot on a freshly formatted /data. The LOS nightly is a
    userdebug build, so its own /system/etc/selinux/plat_sepolicy.cil already has the
    userdebug rules and serves as the sepolicy. Also adds printk.devkmsg=on.
  * --permissive: androidboot.selinux=permissive (honoured by userdebug init).

Usage:
  repack_los_boot.py LOS_boot.img OUT.img [--kernel Image.gz] [--dtb file.dtb]
                     [--uart] [--recovery] [--debuggable plat_sepolicy.cil]
                     [--permissive] [--cmdline-extra "..."]

Test with `fastboot boot OUT.img` before flashing.
"""
import argparse
import gzip
import hashlib
import os
import re
import struct
import subprocess
import sys
import tempfile

DTB_MAGIC = b"\xd0\x0d\xfe\xed"

# Loaded by second-stage init with the highest priority when /force_debuggable exists
# and the device is unlocked (same keys as AOSP system/core/rootdir/adb_debug.prop).
ADB_DEBUG_PROP = b"""# laurus debug boot: adb from early boot, no authorization
ro.debuggable=1
ro.adb.secure=0
persist.sys.usb.config=adb
"""


def align(n, page):
    return (n + page - 1) // page * page


def parse_v2(b):
    if b[:8] != b"ANDROID!":
        sys.exit("not an Android boot image")
    ks, ka, rs, ra, ss, sa, ta, ps, hv, osv = struct.unpack("<10I", b[8:48])
    if hv != 2:
        sys.exit(f"expected header v2, got v{hv}")
    cmdline = b[64:576].split(b"\0")[0] + b[608:1632].split(b"\0")[0]
    ds, da = struct.unpack("<IQ", b[1648:1660])
    o = ps
    kernel = b[o:o + ks]; o += align(ks, ps)
    ramdisk = b[o:o + rs]; o += align(rs, ps)
    o += align(ss, ps)
    rds = struct.unpack("<I", b[1632:1636])[0]
    o += align(rds, ps)
    dtb = b[o:o + ds]
    base = ka - 0x8000
    return dict(kernel=kernel, ramdisk=ramdisk, dtb=dtb, page=ps, osv=osv,
                cmdline=cmdline.decode(), base=base, kernel_off=ka - base,
                ramdisk_off=ra - base, tags_off=ta - base, dtb_addr=da)


def decode_os(osv):
    ver, lvl = osv >> 11, osv & 0x7FF
    a, b_, c = (ver >> 14) & 0x7F, (ver >> 7) & 0x7F, ver & 0x7F
    return f"{a}.{b_}.{c}", f"{2000 + (lvl >> 4)}-{lvl & 0xF:02d}"


# ---- cpio newc ---------------------------------------------------------------

def cpio_read(data):
    entries, i = [], 0
    while True:
        h = data[i:i + 110]
        if h[:6] not in (b"070701", b"070702"):
            sys.exit(f"bad cpio magic at {i}")
        f = [int(h[6 + 8 * k:14 + 8 * k], 16) for k in range(13)]
        namesize, filesize = f[11], f[6]
        name = data[i + 110:i + 110 + namesize - 1].decode()
        j = (i + 110 + namesize + 3) & ~3
        body = data[j:j + filesize]
        i = (j + filesize + 3) & ~3
        entries.append([h[:6], f, name, body])
        if name == "TRAILER!!!":
            return entries


def cpio_write(entries):
    out = bytearray()
    for magic, f, name, body in entries:
        f = list(f)
        f[6], f[11] = len(body), len(name) + 1
        out += magic + b"".join(b"%08X" % v for v in f) + name.encode() + b"\0"
        out += b"\0" * (-len(out) % 4)
        out += body
        out += b"\0" * (-len(out) % 4)
    return bytes(out)


def strip_fstab_flags(text):
    """Remove slotselect / avb* from the fs_mgr flags column (5th field)."""
    out, changed = [], 0
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line); continue
        cols = re.split(r"(\s+)", line.rstrip("\n"))  # keep whitespace tokens
        fields = cols[0::2]
        if len(fields) < 5:
            out.append(line); continue
        flags = fields[4].split(",")
        keep = [x for x in flags if x != "slotselect" and not re.match(r"avb(=|_keys=|$)", x)]
        if keep != flags:
            changed += 1
            cols[8] = ",".join(keep) or "defaults"
        out.append("".join(cols) + ("\n" if line.endswith("\n") else ""))
    return "".join(out), changed


def add_files(entries, files):
    """Insert regular files (name -> bytes, mode 0644, root:root) before the trailer;
    their parent directories must already exist in the archive."""
    names = {e[2] for e in entries}
    ino = max(e[1][0] for e in entries) + 1
    for name, body in files.items():
        parent = os.path.dirname(name)
        if parent and parent not in names:
            sys.exit(f"cannot add {name}: no {parent}/ in the ramdisk")
        if name in names:
            sys.exit(f"{name} already exists in the ramdisk")
        f = [ino, 0o100644, 0, 0, 1, 0, len(body), 0, 0, 0, 0, len(name) + 1, 0]
        entries.insert(len(entries) - 1, [b"070701", f, name, body])
        ino += 1


def patch_ramdisk(rd, extra=None):
    if rd[:2] != b"\x1f\x8b":
        sys.exit("ramdisk is not gzip; extend patch_ramdisk() for this compression")
    entries = cpio_read(gzip.decompress(rd))
    report = []
    for e in entries:
        name = e[2]
        if re.search(r"(^|/)(fstab\.[^/]+|recovery\.fstab)$", name) and e[3]:
            new, n = strip_fstab_flags(e[3].decode())
            if n:
                e[3] = new.encode()
                report.append(f"{name}: {n} line(s) patched")
    for e in entries:
        if e[3] and b"slotselect" in e[3] and re.search(r"fstab", e[2]):
            sys.exit(f"slotselect still present in {e[2]}")
    if extra:
        add_files(entries, extra)
        report += [f"{n}: added ({len(b)} B)" for n, b in extra.items()]
    return gzip.compress(cpio_write(entries), compresslevel=9, mtime=0), report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("boot"); ap.add_argument("out")
    ap.add_argument("--kernel", help="replacement Image.gz (own build)")
    ap.add_argument("--dtb", help="replacement dtb (single or concatenated)")
    ap.add_argument("--uart", action="store_true", help="console=ttyMSM0 + earlycon for TP4711/TP4712")
    ap.add_argument("--recovery", action="store_true", help="omit force_normal_boot (for the recovery partition)")
    ap.add_argument("--debuggable", metavar="PLAT_SEPOLICY_CIL",
                    help="add force_debuggable + adb_debug.prop; the LOS system's plat_sepolicy.cil")
    ap.add_argument("--permissive", action="store_true", help="androidboot.selinux=permissive")
    ap.add_argument("--cmdline-extra", default="")
    a = ap.parse_args()

    img = parse_v2(open(a.boot, "rb").read())
    kernel = open(a.kernel, "rb").read() if a.kernel else img["kernel"]
    dtb = open(a.dtb, "rb").read() if a.dtb else img["dtb"]
    if kernel[:2] != b"\x1f\x8b":
        sys.exit("kernel must be Image.gz (abl expects gzip + appended dtb)")
    if dtb[:4] != DTB_MAGIC:
        sys.exit("dtb has no FDT magic")

    extra = {}
    if a.debuggable:
        cil = open(a.debuggable, "rb").read()
        if b"(typeattribute" not in cil[:65536] and b"(type " not in cil[:65536]:
            sys.exit(f"{a.debuggable} does not look like a CIL sepolicy")
        # init checks these after switching root to /first_stage_ramdisk on
        # recovery-as-boot images; the root copies cover the other code path
        for root in ("", "first_stage_ramdisk/"):
            extra[root + "force_debuggable"] = b""
            extra[root + "adb_debug.prop"] = ADB_DEBUG_PROP
            extra[root + "userdebug_plat_sepolicy.cil"] = cil
    ramdisk, report = patch_ramdisk(img["ramdisk"], extra)

    cmd = img["cmdline"].split()
    if a.debuggable:
        cmd.append("printk.devkmsg=on")
    if a.permissive:
        cmd.append("androidboot.selinux=permissive")
    if a.uart:
        cmd = [c for c in cmd if not c.startswith("console=")]
        cmd += ["console=ttyMSM0,115200n8", "earlycon=msm_geni_serial,0x4a90000"]
    if not a.recovery:
        cmd.append("androidboot.force_normal_boot=1")
    cmd.append("androidboot.vbmeta.device_state=unlocked")
    cmd += a.cmdline_extra.split()
    cmdline = " ".join(cmd)
    if len(cmdline) > 512 + 1024 - 1:
        sys.exit("cmdline too long")

    osver, patch = decode_os(img["osv"])
    with tempfile.TemporaryDirectory() as td:
        kp, rp = os.path.join(td, "Image.gz-dtb"), os.path.join(td, "ramdisk")
        open(kp, "wb").write(kernel + dtb)
        open(rp, "wb").write(ramdisk)
        subprocess.run([
            "mkbootimg", "--header_version", "1",
            "--kernel", kp, "--ramdisk", rp,
            "--base", hex(img["base"]), "--kernel_offset", hex(img["kernel_off"]),
            "--ramdisk_offset", hex(img["ramdisk_off"]), "--second_offset", "0xf00000",
            "--tags_offset", hex(img["tags_off"]), "--pagesize", str(img["page"]),
            "--os_version", osver, "--os_patch_level", patch,
            "--cmdline", cmdline, "-o", a.out], check=True)

    # self-check
    o = open(a.out, "rb").read()
    hv = struct.unpack("<I", o[40:44])[0]
    ks = struct.unpack("<I", o[8:12])[0]
    assert hv == 1 and o[4096 + ks - len(dtb):4096 + ks] == dtb
    if len(o) > 64 * 1024 * 1024:
        sys.exit(f"{a.out} is {len(o)} bytes > 64 MiB boot partition")
    print(f"header v1, os {osver} / {patch}, {len(o)} bytes, sha256 {hashlib.sha256(o).hexdigest()}")
    print("kernel:", a.kernel or "LOS prebuilt", "| dtb:", a.dtb or "LOS prebuilt", f"({len(dtb)} B)")
    for r in report:
        print("ramdisk:", r)
    print("cmdline:", cmdline)


if __name__ == "__main__":
    main()
