#!/usr/bin/env python3
"""Graft CC9e (laurus) bits onto the LOS laurel_sprout vendor.img.

Findings behind the file list (2026-10-24):
  * Both phones register `trinket-qrd-snd-card` (CC9e dmesg, LOS DTB), so the HAL uses
    mixer_paths_qrd.xml and libacdbloader reads /vendor/etc/acdbdata/QRD/. The CC9e IDP/
    set is Qualcomm's generic reference and is never loaded.
  * audio_platform_info_intcodec.xml (the one in use) has identical acdb IDs on both,
    so only the calibration data differs: acdbdata/QRD/*.
  * adsp_avs_config.acdb describes the ADSP firmware module set: take the CC9e copy,
    because the phone keeps its A9 ADSP (5.4-00267).
  * mixer_paths_qrd.xml stays LOS: its control names match the LOS kernel.
  * The 3 vendor modules are replaced with the ones from our kernel build
    (the debug config changes struct module, so LOS's .ko would be rejected).

Metadata (mode, uid, gid, security.selinux) of every replaced file is copied from the
file it replaces. The AVB footer/hashtree is erased (stale after editing; the repacked
boot's fstab no longer has `avb`).

Usage:
  graft_vendor.py --los LOS_vendor.img --cc9e CC9e_vendor.img --modules DIR --out OUT.img
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ACDB_FILES = [f"/etc/acdbdata/QRD/QRD_{n}" for n in (
    "Bluetooth_cal.acdb", "Codec_cal.acdb", "General_cal.acdb", "Global_cal.acdb",
    "Handset_cal.acdb", "Hdmi_cal.acdb", "Headset_cal.acdb", "Speaker_cal.acdb",
    "workspaceFile.qwsp")] + ["/etc/acdbdata/adsp_avs_config.acdb"]
MODULES = ["msm-geni-ir.ko", "rmnet_perf.ko", "rmnet_shs.ko"]


def debugfs(img, cmds, write=False):
    with tempfile.NamedTemporaryFile("w", suffix=".cmds", delete=False) as f:
        f.write("\n".join(cmds) + "\n")
    try:
        r = subprocess.run(["debugfs"] + (["-w"] if write else []) + ["-f", f.name, img],
                           capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    return r.stdout + r.stderr


def stat(img, path):
    """(full st_mode, uid, gid). debugfs prints only permission bits after `Mode:`,
    so the file type is rebuilt from `Type:` (only regular files are replaced)."""
    out = debugfs(img, [f"stat {path}"])
    t = re.search(r"Type:\s+(\S+)", out)
    m = re.search(r"Mode:\s+(\d+)", out)
    u = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)", out)
    if not (t and m and u):
        sys.exit(f"cannot stat {path} in {img}:\n{out}")
    if t.group(1) != "regular":
        sys.exit(f"{path} is {t.group(1)}, expected a regular file")
    return 0o100000 | int(m.group(1), 8), int(u.group(1)), int(u.group(2))


def selinux(img, path, td):
    dst = os.path.join(td, "ctx." + hashlib.md5(path.encode()).hexdigest())
    debugfs(img, [f"ea_get -f {dst} {path} security.selinux"])
    if not os.path.exists(dst) or not open(dst, "rb").read().startswith(b"u:"):
        sys.exit(f"no security.selinux on {path}")
    return dst


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--los", required=True)
    ap.add_argument("--cc9e", required=True)
    ap.add_argument("--modules", required=True, help="dir with the 3 .ko from build-laurus.sh")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        # source files: (vendor path, local file)
        plan = []
        for p in ACDB_FILES:
            local = os.path.join(td, "src" + p.replace("/", "_"))
            debugfs(a.cc9e, [f"dump {p} {local}"])
            if not os.path.exists(local) or os.path.getsize(local) == 0:
                sys.exit(f"{p} missing in {a.cc9e}")
            plan.append((p, local))
        for m in MODULES:
            local = os.path.join(a.modules, m)
            if not os.path.isfile(local):
                sys.exit(f"missing {local}")
            plan.append((f"/lib/modules/{m}", local))

        print(f"copy {a.los} -> {a.out}")
        shutil.copyfile(a.los, a.out)
        # An already-grafted base has no AVB footer; erase_footer then fails with
        # "does not look like a vbmeta image". That is the desired state, not an error.
        r = subprocess.run(["avbtool", "erase_footer", "--image", a.out],
                           capture_output=True, text=True)
        if r.returncode != 0 and "does not look like a vbmeta image" not in (r.stdout + r.stderr):
            sys.exit(f"avbtool erase_footer failed:\n{r.stdout}{r.stderr}")
        print("avb footer already absent" if r.returncode else "avb footer erased")

        cmds = []
        for vpath, local in plan:
            mode, uid, gid = stat(a.out, vpath)
            ctx = selinux(a.out, vpath, td)
            d, name = os.path.split(vpath)
            cmds += [f"cd {d}", f"rm {name}", f"write {local} {name}",
                     f"set_inode_field {name} mode 0{mode:o}",
                     f"set_inode_field {name} uid {uid}", f"set_inode_field {name} gid {gid}",
                     f"ea_set -f {ctx} {name} security.selinux"]
        out = debugfs(a.out, cmds, write=True)
        if re.search(r"(?i)error|not found|failed", out):
            sys.exit(f"debugfs reported problems:\n{out}")

        # verify content + metadata
        for vpath, local in plan:
            chk = os.path.join(td, "chk")
            debugfs(a.out, [f"dump {vpath} {chk}"])
            if sha(chk) != sha(local):
                sys.exit(f"content mismatch after write: {vpath}")
            mode, uid, gid = stat(a.out, vpath)
            ctx = open(selinux(a.out, vpath, td), "rb").read().rstrip(b"\0").decode()
            print(f"  {vpath:45s} {mode:o} {uid}:{gid} {ctx}  sha256 {sha(local)[:12]}")

    r = subprocess.run(["e2fsck", "-fn", a.out], capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)
    if r.returncode not in (0,):
        sys.exit(f"e2fsck exit {r.returncode}:\n{r.stdout}{r.stderr}")
    print(f"{a.out}: {os.path.getsize(a.out)} bytes, sha256 {sha(a.out)}")


if __name__ == "__main__":
    main()
