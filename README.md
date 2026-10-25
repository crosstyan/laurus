# laurus — Xiaomi Mi CC9e on LineageOS 24

Research and build notes for a Xiaomi Mi CC9e (`laurus`, SM6125, A-only, unlocked) running
**LineageOS 24 (Android 17)** with MindTheGapps, **BakaSU** root and **SUSFS** root hiding.
The system/vendor come from the Mi A3 (`laurel_sprout`), which shares the board and most
peripherals; the kernel is a custom 4.14.357 with BakaSU and SUSFS.

This is a research repository, not a ROM distribution. Flashable images and raw device
dumps are kept locally (see [Public snapshot](#public-snapshot)).

## Status (2026-10-25)

Working:

- audio, all five cameras, ~30 sensors, Wi-Fi, Bluetooth and fingerprint
- **SIM/telephony tested and working**
- MindTheGapps 17, root (`u:r:ksu:s0`), SELinux **enforcing**, SUSFS hiding
- Clash Meta VPN (`allow_bypass=false`), Xiaomi CN captive-portal probe

Known limitations:

- SUSFS `OPEN_REDIRECT`, `SUS_MAP` and `ENABLE_LOG` are off by design (image size / first boot).
- The BakaSU manager package itself is visible to package enumeration; use its hide-manager
  feature if a detector lists packages.
- `kernel/bakasu-manual-hooks-4.14.patch` still has the post-execve `filename` use-after-free;
  it applies only to the manual-hook flavor, not the running SUSFS kernel.
- The saved Wi-Fi network does not always auto-reconnect after a reboot; tap it in Settings.
- `ReSuSFS_apply-settings.sh` is deliberately disabled (it would turn adb/developer options off).

## Current stack

Images live in the local `flash/` directory, not in this repository. Boot and vendor are a pair:
module signatures are per build.

| partition | image | contents |
|---|---|---|
| boot | `boot-susfs-main-perf-enforcing.img` (sha256 `41e1d8f5…1d1bb2`, header v1) | LOS 4.14.357 perf SUSFS kernel (`laurus-susfs-main`; flashed tree `16b58dc`, published tip `71adeaf`), BakaSU main 35252/uapi 6, preinit, SELinux enforcing, adb |
| vendor | `vendor-laurus-fix10.img` (sha256 `2d64bf3d…0039de`) | fix8 (fstab patched, boot-control `.rc` removed) + the main build's three modules |
| system | `system-gapps.sparse.img` | LOS 24 nightly 20261020 + MindTheGapps 17, offline-installed, fs grown to 5 GiB |
| dtbo | LOS `dtbo.img` | unchanged from LOS |
| vbmeta | untouched (stock, flags `0x3`) | never reflashed while running a non-stock system |
| recovery | untouched TWRP 3.3.1 (wzsx150) | |
| userdata / metadata | userdata erased; LOS formats f2fs | **metadata must be `fastboot format:ext4`**; erase alone means endless boot |
| firmware (abl/xbl/tz/modem/dsp/…) | untouched, CC9e Android 9 | |

Rollback pairs: previous SUSFS pair `boot-susfs-perf-enforcing.img` +
`vendor-laurus-fix8.img`; permissive audit pair `boot-susfs-permissive-rollback.img` +
`vendor-laurus-fix6.img`; root-only `boot-bakasu-rc3-adb-permissive.img` +
`vendor-laurus-fix4.img`. Flash both halves when reverting.

## Root and hiding

- Driver/manager: BakaSU main **35252** (uapi 6, `v4.2.0-rc3-d5e9e025`); manager shows
  “Working / Built-in”.
- Kernel: SUSFS **v2.3.0** non-GKI, ported from `susfs4ksu` (`gki-android12-5.10` @ `5419f4e`)
  with eight audit fixes. Inline-hook mode; `CONFIG_KSU_MANUAL_HOOK` is not set.
- Features on: `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`, `SPOOF_UNAME`,
  `HIDE_KSU_SUSFS_SYMBOLS`, `SPOOF_CMDLINE_OR_BOOTCONFIG`.
- Userspace: **ReSuSFS v26.10.23** (`ahmed-alnassif/ReSuSFS`), `HIDE_SUS_MNTS_NON_SU=1`,
  `ENABLE_AVC_LOG_SPOOFING=1`, `ENABLE_LOG=0`.
- SELinux is enforcing at boot; Trust reports Enforcing. Uname, green/user props and
  `/proc/cmdline` spoofing are verified and survive reboot.
- `/data/adb/ksud` still prints `4.2.0-rc3 (uapi: 4)`; the 35252 manager uses its bundled
  `libksud.so`, and the old binary runs the ReSuSFS scripts. This is expected, not a downgrade.
- `ksu_susfs` is the manager's `ksud` hardlink (supports the newer `config` subcommands).
- Ruru v1.1.1 cannot be installed on Android 17 (old targetSdk blocked by Play Protect);
  detection spot checks were done manually.

## Kernel

Kernel fork: <https://github.com/crosstyan/android_kernel_xiaomi_sm6125>

| branch | tip | contents |
|---|---|---|
| `laurus-susfs-main` (default) | `71adeaf` | BakaSU main `d5e9e025` + SUSFS v2.3.0; source vendored |
| `laurus-bakasu` | `a82d1e2` | BakaSU manual hooks; source vendored |

Both are based on `LineageOS/android_kernel_xiaomi_sm6125` `lineage-24.0` @ `8aaa002`.
The BakaSU source is vendored in `drivers/kernelsu`; clones build without a local symlink.
Commit hashes were rewritten to use the GitHub noreply email. `71adeaf` is the flashed
`16b58dc` kernel code plus the vendored BakaSU source. The running kernel still reports
`4.14.357-openela-perf-susfs-g16b58dc8d946`.

Key kernel constraints:

- The ABL's 64-bit kernel window is **52 MiB** (`KernelLoadAddr = BaseMemory | 0x80000`,
  `KernelEndAddr = BaseMemory + 0x3400000`); 61.84 MiB resets. The ABL checks the
  **decompressed blob** (`KernelSizeActual`), not the arm64 `image_size`. Aim ≤48 MiB and
  check both. Details: `notes/abl-bootlinux.md` and `notes/bringup-2026-10-25.md`.
- Keep `CONFIG_FTRACE=y` in the perf config: `CONFIG_BPF_EVENTS` depends on it, and without the
  GPU-mem BPF maps Android's `system_server` aborts in `libmeminfo` every ~10 s.
- Flash `boot` and `vendor` together; module signatures are per build.

Build recipe: `kernel/README.md`.

## Hardware and key findings

- Mi A3 (`laurel_sprout`) and Mi CC9e (`laurus`) are the same hardware family
  (board `S88512AA1`, panel, cameras, sensors). Camera/sensor configs are shared.
- Audio: both register `trinket-qrd-snd-card` and load `mixer_paths_qrd.xml` +
  `acdbdata/QRD/`; the mixer paths are byte-identical. The CC9e-specific difference is the QRD
  calibration data (`acdbdata/QRD/*`, `adsp_avs_config.acdb`). The in-use
  `audio_platform_info_intcodec.xml` has identical acdb IDs on both.
- Cameras: Sony IMX586 48 MP main, Samsung S5K4H7 8 MP ultrawide, OmniVision OV02A10 2 MP
  depth, Samsung S5KGD1 32 MP front; Camera2 `supportedHardwareLevel=3` on all camera devices.
- Partitioning: 4K logical blocks (GPT header at offset 4096, not 512). `system` is
  non-dynamic 5120 MiB; `vendor` 1024 MiB; the CC9e is A-only.
- `vbmeta` flags are `0x3` (verity + verification disabled); never relock.
- LOS A/B images on this A-only phone need `slotselect`/`avb` removed from both the ramdisk
  fstab and `/vendor/etc/fstab.qcom`, and the boot-control HAL removed; details in
  `notes/bringup-2026-10-25.md`.
- Module signing keys are per kernel build (stock laurus SHA-512, LOS SHA-256, our debug kernel
  signing off), so each module set loads only into its own kernel.

## Repository guide

| path | contents |
|---|---|
| `PLAN.md` | historical plan, phases and decisions |
| `notes/cc9e-notes.md` | device state, AVB/vbmeta, partition map, EDL/UART, root/hiding |
| `notes/hardware.md` | hardware inventory and A3-vs-CC9e research |
| `notes/bringup-2026-10-25.md` | field report: two failed first boots (kernel size, `/metadata`, vendor slotselect) and fixes |
| `notes/fresh-install-2026.md` | audited 2019 guide + 2026 clean-install runbook |
| `notes/los-upgrade.md` | LOS upgrade without wiping on this A-only device |
| `notes/partition-table.md` | full 6-LUN GPT table (84 by-name partitions) |
| `notes/avb-vbmeta.md` | AVB/vbmeta layout, dm-verity, Magisk/fstab gates |
| `notes/abl-bootlinux.md` | ABL BootLinux decompilation: 52 MiB kernel window |
| `notes/gcam.md` | GCam/LMC/PhotonCamera research and APK archive |
| `kernel/README.md` | BakaSU/SUSFS kernel build recipe |
| `tools/` | `repack_los_boot.py`, `graft_vendor.py`, GApps installer, boot-log capture |
| `misc/vendor_compare/SOURCES.md` | provenance/hashes for the audio-config comparison |
| `backups/2026-10-25/SHA256SUMS` | hashes for the local 25-image partition backup |

## Public snapshot

Raw unit dumps (`logs/`, `artifacts/`, `analysis/`, `firmware/`, `out/`), partition images and
the vendor audio XMLs (`misc/vendor_compare/*.xml`) are kept out of this repository. They contain
unit identifiers (serial, IMEI/MEID, Wi-Fi/Bluetooth MACs, camera fuse IDs) or vendor-restricted
files. The analysis, tooling and kernel patches are public; the raw evidence stays local.
`S88512AA1` is the public board code, not the unit serial.

## Safety

- Never flash bootloader/firmware partitions (`abl`, `xbl`, `tz`, `hyp`, `devcfg`, `modem`, `dsp`, …).
- Never relock; keep `vbmeta` at flags `0x3`.
- Never flash the LOS payload's firmware images; only `system`, `vendor`, `boot`, `dtbo`.
- `fastboot boot` is not supported by this ABL; every test means flashing `boot` (and
  `vendor` when changing kernels).
- The GPT uses 4K blocks; restore only the GPT ranges, never whole 1 MiB head/tail dumps.
- Keep the partition backup and the laurus V10.2.13.0 fastboot ROM for recovery; EDL is the
  last resort (TP4728/TP4729).
- Debug: `logcat -b all`, pstore (`/sys/fs/pstore/console-ramoops-0`), TWRP on `recovery`, UART
  (TP4711 TX + TP4719 GND, 1.8 V, 115200; kernel output only with the debug kernel).
