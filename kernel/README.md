# laurus kernel (LOS sm6125 lineage-24.0, 4.14.357) — root builds

Working: **BakaSU** (ex-ReSukiSU) in manual-hook mode; the manager shows "Working / Built-in".

Public fork: <https://github.com/crosstyan/android_kernel_xiaomi_sm6125>
(`laurus-susfs-main` = BakaSU main + SUSFS; `laurus-bakasu` = BakaSU manual hooks).

## Recipe

Kernel tree: `LineageOS/android_kernel_xiaomi_sm6125` @ `8aaa002` (lineage-24.0),
local clone `/mnt/hdd/laurus/kernel/android_kernel_xiaomi_sm6125`.

1. `git worktree add ../sm6125-bakasu HEAD`; in it: vendor `BakaSU/kernel` as
   `drivers/kernelsu` (the published `laurus-*` branches already do; `ln -s
   ../../BakaSU/kernel drivers/kernelsu` also works locally), append
   `obj-$(CONFIG_KSU) += kernelsu/` to `drivers/Makefile`, and add
   `source "drivers/kernelsu/Kconfig"` before `endmenu` in `drivers/Kconfig`.
2. `git apply bakasu-manual-hooks-4.14.patch` — `fs/exec.c`, `fs/open.c`, `fs/stat.c`,
   `kernel/reboot.c`: the bakasu.org/guide/manual-integrate hooks in their 4.14 variants
   (execve + post-execve, faccessat 4.19−, stat + newfstat/fstat64 return, reboot). The
   BakaSU build checks every hook and fails if one is missing.
3. Config fragment `laurus-bakasu.config` (KSU, KSU_MANUAL_HOOK, setuid/init.rc via LSM,
   input via input_handler). `KALLSYMS_ALL=y` in the LOS config makes the documented
   static-symbol exports unnecessary.
4. `build-laurus.sh bakasu build` → `Image.gz` (header `image_size` 51.93 MiB; the ABL's
   64-bit window is 52 MiB: `KernelLoadAddr = BaseMemory | 0x80000`,
   `KernelEndAddr = BaseMemory + 0x3400000`; 61.84 MiB resets) plus the 3 vendor modules
   signed with this build's key. The “48.3 MiB” LOS figure is the decompressed `Image`; the
   bootloader checks the **decompressed blob** (`KernelSizeActual`), not `image_size`.
   Details: `notes/abl-bootlinux.md`.
5. Boot image: `tools/repack_los_boot.py LOS_boot.img out.img --kernel Image.gz
   [--debuggable plat_sepolicy.cil] [--permissive]`; vendor: replace `/vendor/lib/modules/*.ko`
   with this build's modules.

Versions: BakaSU main `d5e9e025` (**driver 35252 / uapi 6**) with manager BakaSU 35252
(versionName `v4.2.0-rc3`): "Working / Built-in", no warning. The manager's bundled
`libksud.so` speaks uapi 6; `/data/adb/ksud` may still print `4.2.0-rc3 (uapi: 4)` and runs
the ReSuSFS scripts fine.

## SUSFS flavor (current kernel)

Root hiding, working. Worktree `/mnt/hdd/laurus/kernel/sm6125-susfs`, branch
**`laurus-susfs-main`** (published tip `71adeafb7174`; same kernel code as the flashed
pre-rewrite `16b58dc8d946`, hashes rewritten for noreply email; BakaSU main `d5e9e025` +
preinit wiring; BakaSU source vendored in `drivers/kernelsu`),
`CONFIG_KSU_SUSFS=y` selects BakaSU's
**inline-hook** mode (`CONFIG_KSU_MANUAL_HOOK` is not set), so the manual-hook patch above is
not used. SUSFS v2.3.0 (non-GKI) was forward-ported from `susfs4ksu`
`gki-android12-5.10` @ `5419f4e`, then audited: 8 fixes (sus_mount mnt_id lifetime, sdcardfs
`show_options2`, fanotify_fdinfo prototype, smaps_rollup swap leak, `ksu_handle_sys_read`
prototype, readdir EOF, cmdline-spoof consumer, fsnotify mark lifetime). The port's working
record is `/mnt/hdd/laurus/kernel/SUSFS-PORT.md`, sources in `susfs-port-kit/`.

- Current pair: `./build-laurus.sh susfs-perf build` → `out-susfs-perf/` (debug-trimmed:
  DEBUG_INFO/SCHED_DEBUG/SCHEDSTATS off; image in-memory **51.93 MiB**, release
  `4.14.357-openela-perf-susfs-g16b58dc8d946`).
  Boot image (enforcing): `tools/repack_los_boot.py LOS_boot.img
  images/boot-susfs-main-perf-enforcing.img --kernel out-susfs-perf/arch/arm64/boot/Image.gz
  --cmdline-extra "androidboot.selinux=enforcing"` → sha256 `41e1d8f5…960d1bb2`.
  Permissive test image: `boot-susfs-main-perf-adb-permissive.img` → sha256 `21994d7b…bbb6a`;
  `preinit=0` fallbacks are `boot-susfs-main-perf-{enforcing,adb-permissive}-preinit0.img`
  (`1b2d7ac4…` / `6cc2a335…`).
  Vendor: **clone the current grafted `vendor-laurus-fix8.img`** and replace the 3 modules with
  `out-susfs-perf/modules/*` → `vendor-laurus-fix10.img` (sha256 `2d64bf3d…c0039de`).
  Do **not** re-graft from raw LOS for a module-only update: `graft_vendor.py` does not patch
  the vendor fstab or remove the boot-control `.rc`, so fix9 reintroduced both and vold waited
  forever. The tool now tolerates an already-erased AVB footer, so passing fix8 as `--los`
  is safe and preserves its fstab/`.rc` edits.
  Module signatures are per build: **flash boot and vendor together**.
- `drivers/kernelsu` is a shared symlink. The current branch points it at
  `../../BakaSU/kernel`; switching back to `laurus-susfs` requires re-pointing it to
  `../../BakaSU-rc3/kernel`.
- Preinit: BakaSU main enables it by default. Good boot: `dmesg | grep -i preinit` →
  `runner staged (15608 bytes)` then `exec runner via /proc/self/fd/6`; Android continues.
  Keep the `preinit=0` repacks for isolation.
- **Keep `CONFIG_FTRACE=y`.** `CONFIG_BPF_EVENTS` depends on it; disabling FTRACE makes
  system_server abort in `libmeminfo` (`BpfMapRO::abortOnMismatch`) every ~10 s and boot never
  completes. `FRAME_POINTER` is forced by arm64; `DEBUG_LIST` is pulled in by
  `BUG_ON_DATA_CORRUPTION` (kept). `INIT_ON_ALLOC_DEFAULT_ON` is also kept.
- Rollback: previous pair `boot-susfs-perf-enforcing.img` (`5fde9fbc…`) +
  `vendor-laurus-fix8.img` (`7b30018e…`); older permissive/audit pair
  `boot-susfs-permissive-rollback.img` (`404237b8…`) + `vendor-laurus-fix6.img`
  (`309e60d3…`).
- Features on: SUS_PATH, SUS_MOUNT, SUS_KSTAT, SPOOF_UNAME, HIDE_KSU_SUSFS_SYMBOLS,
  SPOOF_CMDLINE_OR_BOOTCONFIG. Off by design: OPEN_REDIRECT, SUS_MAP, ENABLE_LOG (size).
- Deviation: the `50_add` hooks in `security/selinux/{hooks,selinuxfs}.c` were reverted to
  stock LOS because they call `my_setprocattr`/`my_write_{context,access}`, which only exist
  after `10_enable_susfs_for_ksu.patch`; rc3 keeps `my_write` only. rc3's runtime SELinux
  patching is used instead; the manager still reports SUSFS active.
- Userspace configuration: ReSuSFS v26.10.23 KernelSU module (see `README.md` and
  `notes/cc9e-notes.md` §14). Its default `scripts_bootcompleted.txt` omits
  `ReSuSFS_apply-uname.sh`; add it if uname must be spoofed every boot (it is added here).
  Props/paths/cmdline entries already run at boot-completed.

## Other files

- `build-laurus.sh` — `ref` (LOS config), `debug`, `sukisu`, `bakasu`, `susfs` flavors.
- `laurus-debug.config` — debug fragment (UART console, tracing). Too large for the abl
  (61.84 MiB in memory) as is.
- `/mnt/hdd/laurus/kernel/SUSFS-PORT.md` — the SUSFS 4.14 port record (done, flashed).

## Dead ends (for reference)

- SukiSU-Ultra `main`/`builtin`: assumes the 4.19+ arm64 pt_regs syscall ABI and 5.x kernel APIs.
- SukiSU v4.1.2 + tanranv5/laurus compat patches (branch `laurus-4.1.2` in
  `/mnt/hdd/laurus/kernel/SukiSU-Ultra`): boots; fixed a PAN fault in the reboot kprobe
  (`PT_REAL_REGS`), `TWA_RESUME` mapped to 0 (fd install ran in `do_exit`), and ported the
  packages.list observer to 4.14 fsnotify. The manager still showed "Unsupported": app
  processes never received the driver fd.
