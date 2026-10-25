#!/usr/bin/env python3
"""Install MindTheGapps into a LOS system.img offline (debugfs), mirroring the zip's
update-binary, for a phone whose recovery is too old to run the installer.

What the MindTheGapps installer does, and what this replicates:
  * copy the zip's system/ tree into <system root>/system/ (product/ and system_ext/
    are plain directories on this non-dynamic layout)
  * dirs 0755, files 0644 (0755 for *.sh and extensionless files), root:root,
    files labelled u:object_r:system_file:s0 (new dirs get system_file too)
  * drop product/priv-app/VelvetTitan (only for tangorpro)
  * generate addon.d/30-gapps.sh from addond_head + file list + addond_tail
  * remove system_ext/priv-app/Provision if present (LOS 24 has none; it uses
    LineageSetupWizard, which coexists with Google's SetupWizard)
Before copying, the filesystem is grown to --size (the CC9e system partition is 5 GiB);
the LOS image's AVB footer/hashtree is overwritten, which is fine because the boot
repack removes `avb` from the fstabs.

Usage:
  install_gapps_offline.py --system LOS_system.img --gapps MindTheGapps-*.zip
                           --out system-gapps.img [--size 5120M]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

CTX = b"u:object_r:system_file:s0\0"


def run(*cmd, ok=(0,)):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode not in ok:
        sys.exit(f"{' '.join(cmd)} failed ({r.returncode}):\n{r.stdout}{r.stderr}")
    return r.stdout + r.stderr


def debugfs(img, cmds, write=False):
    with tempfile.NamedTemporaryFile("w", suffix=".cmds", delete=False) as f:
        f.write("\n".join(cmds) + "\n")
    try:
        return run("debugfs", *(["-w"] if write else []), "-f", f.name, img)
    finally:
        os.unlink(f.name)


def exists(img, path):
    return "File not found" not in debugfs(img, [f"stat {path}"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--system", required=True)
    ap.add_argument("--gapps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="5120M", help="grow the filesystem to this size")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        zipfile.ZipFile(a.gapps).extractall(td)
        src = os.path.join(td, "system")
        shutil.rmtree(os.path.join(src, "product/priv-app/VelvetTitan"), ignore_errors=True)
        ad = os.path.join(src, "addon.d")
        files = sorted(os.path.relpath(os.path.join(r, f), src)
                       for r, _, fs in os.walk(src) for f in fs
                       if not os.path.relpath(r, src).startswith("addon.d"))
        with open(os.path.join(ad, "30-gapps.sh"), "w") as out:
            out.write(open(os.path.join(ad, "addond_head")).read())
            out.write("".join(f + "\n" for f in files))
            out.write(open(os.path.join(ad, "addond_tail")).read())
        os.unlink(os.path.join(ad, "addond_head"))
        os.unlink(os.path.join(ad, "addond_tail"))
        ctx = os.path.join(td, "ctx")
        open(ctx, "wb").write(CTX)

        print(f"copy {a.system} -> {a.out}, grow to {a.size}")
        shutil.copyfile(a.system, a.out)
        run("truncate", "-s", a.size, a.out)
        run("e2fsck", "-fy", a.out, ok=(0, 1))
        run("resize2fs", a.out)

        dirs, regs = [], []
        for r, ds, fs in os.walk(src):
            rel = os.path.relpath(r, src)
            for d in sorted(ds):
                dirs.append(os.path.normpath(os.path.join(rel, d)))
            for f in sorted(fs):
                regs.append(os.path.normpath(os.path.join(rel, f)))
        cmds = []
        for d in dirs:
            p = f"/system/{d}"
            if not exists(a.out, p):
                cmds += [f"mkdir {p}", f"set_inode_field {p} mode 040755",
                         f"set_inode_field {p} uid 0", f"set_inode_field {p} gid 0",
                         f"ea_set -f {ctx} {p} security.selinux"]
        for f in regs:
            p = f"/system/{f}"
            ext = f.rsplit("/", 1)[-1]
            mode = "0100755" if f.endswith(".sh") or "." not in ext else "0100644"
            if exists(a.out, p):
                cmds.append(f"rm {p}")
            cmds += [f"write {os.path.join(src, f)} {p}", f"set_inode_field {p} mode {mode}",
                     f"set_inode_field {p} uid 0", f"set_inode_field {p} gid 0",
                     f"ea_set -f {ctx} {p} security.selinux"]
        out = debugfs(a.out, cmds, write=True)
        bad = [l for l in out.splitlines() if any(k in l.lower() for k in ("error", "not found", "fail", "no space"))]
        if bad:
            sys.exit("debugfs problems:\n" + "\n".join(bad[:20]))
        if exists(a.out, "/system/system_ext/priv-app/Provision"):
            sys.exit("Provision present: remove it (not expected on LOS 24)")

        # verify every file: content, mode, context
        for f in regs:
            p = f"/system/{f}"
            chk = os.path.join(td, "chk")
            debugfs(a.out, [f"dump {p} {chk}"])
            if open(chk, "rb").read() != open(os.path.join(src, f), "rb").read():
                sys.exit(f"content mismatch: {p}")
            if "system_file" not in debugfs(a.out, [f"ea_list {p}"]):
                sys.exit(f"missing context: {p}")
        print(f"installed {len(regs)} files, {len(dirs)} dirs (VelvetTitan dropped)")

    r = subprocess.run(["e2fsck", "-fn", a.out], capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1])
    if r.returncode != 0:
        sys.exit(f"e2fsck exit {r.returncode}:\n{r.stdout}{r.stderr}")


if __name__ == "__main__":
    main()
