# laurus — plan (Android 16/17 on the CC9e, no unnecessary builds)

## Goal

Run a modern LineageOS (24.0 / Android 17) system on the Xiaomi Mi CC9e (`laurus`,
S88512AA1, SM6125) with working camera/audio/sensors/telephony, without bricking and
without building Android unless the official build fails.

## Outcome — achieved (2026-10-25)

**Goal met via Phase 3** (LOS A3 images + audio graft + custom kernel), plus GApps and
root. The CC9e now boots **LineageOS 24 (Android 17)** to the setup wizard with working
audio, all 5 cameras, ~30 sensors, Wi-Fi, fingerprint, Bluetooth and SIM/telephony
(tested and working). **Google services** (MindTheGapps 17) and **root** (BakaSU main 35252) are
installed; `adb shell su -c id` → `uid=0(root) … context=u:r:ksu:s0`. No Android build was
needed. The bootloader was never relocked and no bootloader/firmware partition was flashed.

Current stack and exact flashed images: **`README.md`** and **`kernel/README.md`**.
Future LOS updates without wiping userdata: **`notes/los-upgrade.md`** (manual system/vendor
swap; the A/B Updater cannot work on this A-only device). What's flashed now, by partition:

| partition | image | contents |
|---|---|---|
| system | `system-gapps.sparse.img` | LOS 24 nightly 20261020 + MindTheGapps 17 (offline-installed, fs grown to 5 GiB) |
| vendor | `vendor-laurus-fix10.img` | fix8 + the main SUSFS kernel's 3 modules (per-build signed, so boot+vendor are a pair) |
| boot | `boot-susfs-main-perf-enforcing.img` | LOS 4.14.357 perf kernel (`susfs-perf`, `laurus-susfs-main` flashed tree `16b58dc`; published tip `71adeaf`) + BakaSU main 35252/uapi 6 (inline hooks, preinit) + **SUSFS v2.3.0**, header v1, **SELinux enforcing**, adb |
| dtbo | LOS `dtbo.img` | unchanged from LOS |
| vbmeta | **untouched** (stock, flags 0x3) | never reflashed while running non-stock |
| recovery | **untouched** TWRP 3.3.1 (wzsx150) | |
| firmware (abl/xbl/tz/modem/dsp/…) | **untouched**, CC9e Android 9 | never flashed |

Root manager: BakaSU 35252 (versionName `v4.2.0-rc3`), matched to the kernel driver
35252/uapi 6 ("Working / Built-in"). **Root hiding:** SUSFS v2.3.0 was ported to 4.14,
audited (8 fixes: mnt_id lifetime, sdcardfs options, fdinfo prototype, smaps rollup, read
syscall prototype, readdir EOF, cmdline consumer, fsnotify mark lifetime), debug-trimmed
(`susfs-perf`), built into the boot image and flashed with `vendor-laurus-fix10.img` (boot
sha256 `41e1d8f5…`, vendor `2d64bf3d…`). **SELinux is enforcing at boot**
(`androidboot.selinux=enforcing`); Trust shows Enforcing, root/SUSFS/manager verified. A few
vendor-init AVCs remain (not root/kernel). The **ReSuSFS v26.10.23** KernelSU module
(`ahmed-alnassif/ReSuSFS`) applies the hiding config: sus_path/mount/kstat hiding, uname +
props + **cmdline** spoofing, avc-log spoofing; `apply-settings.sh` (adb off) stays disabled.
`ReSuSFS_apply-uname.sh` was added to its boot-completed list (it is not a default entry).
Detection: Ruru v1.1.1 previously reported all 8 checks "Not Found"; on Android 17 Play
Protect now blocks that old-targetSdk APK, so hiding was spot-checked manually. Kernel branch
`laurus-susfs-main` flashed tree `16b58dc8d946`; published tip `71adeaf`; see `/mnt/hdd/laurus/kernel/SUSFS-PORT.md`.

## Starting state (original phone, before the cross-flash)

| layer | value |
|---|---|
| hardware | CC9e `laurus`, S88512AA1, `ro.boot.hwc=CN`, sku 394 |
| system | Mi A3 `laurel_sprout` V10.3.4.0 (Android 9) — non-dynamic, 5 GB |
| vendor | laurus V10.2.13.0 (Android 9, VNDK **28**, HIDL target-level **3**) |
| boot | laurus `4.14.98-perf+` (Aug 2019), Magisk 27 patched |
| vbmeta | flags **0x3** (hashtree + verification disabled), rollback 0 |
| bootloader | unlocked (`orange`), `flash.locked=0` |
| backups | partition images at `/mnt/hdd/laurus/project-data/backups/2026-10-25/` (25 + sda GPT, 7.5 GiB); manifest `backups/2026-10-25/SHA256SUMS` in repo; full dump `/mnt/hdd/laurus/full-backup-2026-10-25/` (83 partitions, 6 LUN GPTs, userdata tars for user 0; Guest user 10 intentionally skipped; `BACKUP_REPORT.md`) |
| restore ROM | official laurus V10.2.13.0 (A9) fastboot ROM, firmware byte-identical to the phone (`/mnt/hdd/laurus/downloads/rom-a9/`) |

## Decisions

1. **Non-dynamic system**: single `system` partition, no `super`, **no GPT changes**.
2. **Use the official LOS 24 A3 build** first (no Android build):
   `lineage-24.0-20261020-nightly-laurel_sprout-signed.zip`
   sha256 `a51c1f976e49c4b24b19f9190015d2632cf4b525946c738b2d36a368c4473328`, 1.21 GB (1.12 GiB).
   It is a **payload OTA** (A/B style) → extract images, don't flash the zip on the A-only CC9e.
   The payload also carries A3 bootloader/firmware images (abl, xbl, tz, modem, dsp, …):
   flash only `system`, `vendor`, `boot`, `dtbo`.
3. **Vendor strategy**:
   - Phase 2 keeps the laurus A9 vendor (VNDK 28) — cheapest test.
   - Phase 3 uses the LOS-built A3 A11 vendor (VNDK 30) + **laurus audio calibration graft**
     (`acdbdata/QRD/*` + `adsp_avs_config.acdb` from the CC9e A9 vendor; mixer paths stay LOS).
   - `persist` (per-unit calibration) is never touched.
4. **Kernel**: LOS `android_kernel_xiaomi_sm6125` (lineage-24.0, 4.14.357-openela). The LOS
   vendor has only 3 modules (`msm-geni-ir`, `rmnet_perf`, `rmnet_shs`); everything else is
   built in. Module signing keys are per build, so modules pair with exactly one kernel:
   - LOS prebuilt boot ↔ LOS's own 3 `.ko` (SHA-256, `MODULE_SIG_FORCE=y`);
   - our debug kernel (`/mnt/hdd/laurus/kernel/build-laurus.sh debug`, signing off) ↔ the 3
     `.ko` from that build, which `vendor-laurus.img` carries.
   Stock laurus kernels (SHA-512, `MODULE_SIG_FORCE=y`) pair only with their own vendor's modules.
   *The kernel now in use is the perf SUSFS flavor on BakaSU main: BakaSU 35252/uapi 6
   inline hooks + preinit + the SUSFS v2.3.0 4.14 port (`build-laurus.sh susfs-perf`, signing
   on, SHA-256, SELinux enforcing); its 3 modules are grafted into
   `vendor-laurus-fix10.img`.*
5. **vbmeta**: keep flags 0x3 (or re-apply `--disable-verity --disable-verification`);
   never relock the bootloader.
6. **Root + hiding**: BakaSU main `d5e9e025` (driver/manager 35252, uapi 6), with SUSFS v2.3.0
   compiled in (inline hooks replace the manual-hook patch) and the ReSuSFS module on top for
   configuration. Keep the manager and driver matched; a 35252 manager on a 35171 driver shows
   "Kernel update required". Recipe in `kernel/README.md`. SukiSU-Ultra was tried first and
   abandoned (manager stayed "Unsupported" on this 4.14 ABI).

> **Status (2026-10-25):** Phases 0, 1, 3 done — this is how the Outcome above was reached.
> Phase 2 skipped (VNDK wall, as predicted). Phase 4 (full laurus build) not needed.
> Kept below as the record of how it was done and the reasoning behind each step.

## Phase 0 — prep (Linux workstation) ✓

- [x] copy this project (done via rsync)
- [x] verify backups: `cd /mnt/hdd/laurus/project-data/backups/2026-10-25 && sha256sum -c ~/Projects/laurus/backups/2026-10-25/SHA256SUMS`
- [x] tools: `payload_dumper` (or `payload-dumper-go`), `avbtool`, `e2fsprogs`
      (`debugfs`/`e2fsdroid`), `dtc`, `mkbootimg`/`magiskboot`, `fastboot`
- [x] download the LOS 24 payload (sha256 above)

## Phase 1 — extract the LOS payload ✓

- [x] `payload_dumper payload.bin --out images/` → `system.img`, `vendor.img`, `boot.img`,
      `dtbo.img`, `vbmeta.img`, …
- [x] verify: `system.img` ≤ 5 GB (CC9e partition), `vendor.img` ≤ 1 GB
- [x] record `ro.build.fingerprint` from the extracted system (or `build.prop`)

## Phase 2 — system-only test (cheap, reversible) — skipped

Keep the current laurus `boot` + `vendor`; swap only the system.

- [ ] `fastboot flash system system.img`
- [ ] boot; if it comes up: run the hardware smoke test (camera, earpiece, speaker, Wi-Fi,
      mobile data, sensors, fingerprint)
- [ ] if it hangs: capture `adb logcat -b all -d`, or pstore (`console-ramoops-0`)
- [ ] rollback: `fastboot flash system /mnt/hdd/laurus/project-data/backups/2026-10-25/system.img`

Expected failure mode: VNDK/LLNDK mismatch (vendor 28 vs system ~34/35). Android 17 no
longer supports a VNDK 28 / target-level 3 vendor (sepolicy mapping, VINTF), so this phase is
expected to fail without telling much; skipping straight to Phase 3 is reasonable.

## Phase 3 — full A3 stack + audio overlay ✓ (the route taken)

The successful path. Final boot/vendor differ from the first drafts below: the custom
kernel in use is the **BakaSU rc3** build (`boot-bakasu-rc3-adb-permissive.img`) paired
with `vendor-laurus-fix4.img` (same graft + that kernel's modules). The early
`boot-laurusdbg-*`/`vendor-laurus.img` pairing was the first-boot bring-up.

- [x] boot: header v1, `slotselect`/`avb` stripped, adb from early boot. This abl has
      **no `fastboot boot`**, so boot is flashed every test; fastboot only works from the Mac
      (`~/Projects/laurus/flash/`). The A/B boot-control HAL (`android.hardware.boot-service.qti`)
      had to be removed from vendor or vold never mounts `/data`. `/metadata` must be a real
      ext4 (`fastboot format:ext4`), not just erased. Timeline and evidence of the two failed
      first boots: `notes/bringup-2026-10-25.md`.
- [x] dtbo: LOS `dtbo.img` (`/mnt/hdd/laurus/graft/los/`); vbmeta: kept the current one (flags 0x3)
- [x] build the vendor graft (`tools/graft_vendor.py`): replace `etc/acdbdata/QRD/*` and
      `etc/acdbdata/adsp_avs_config.acdb` with the CC9e A9 versions, and `lib/modules/*.ko`
      with this kernel's build. This script does not touch the vendor fstab or the
      boot-control HAL; those were manual `debugfs` edits in `vendor-laurus-fix1` (see the
      field report). **Do not re-graft from raw LOS for a module-only update** — that
      reintroduces `slotselect` and the boot-control `.rc`; start from the current grafted
      vendor (`vendor-laurus-fix8` → `fix10`) so those edits survive. Keep LOS
      `mixer_paths_qrd.xml` (control names match the LOS
      kernel) and `audio_platform_info*.xml` (acdb IDs already identical). Not IDP: both
      phones use the `trinket-qrd-snd-card` card, so `acdbdata/IDP/` is never loaded.
- [x] flash the repacked vendor; audio/cameras/sensors/Wi-Fi/fingerprint/BT confirmed working
- [x] GApps: MindTheGapps 17 installed offline into the system image (`tools/install_gapps_offline.py`)
- [x] root: BakaSU 35252 (SUSFS inline hooks), manager 35252/uapi 6, Shell root verified
- rollback if needed: `fastboot flash vendor /mnt/hdd/laurus/project-data/backups/2026-10-25/vendor.img`

## Phase 4 — optional laurus build — not done (not needed)

Only if a permanent, laurus-branded, reproducible build is wanted. Phase 3 met the goal
without it, so this was not pursued.

- [ ] `repo` sync LOS 24 (~120 GB) + out (~60 GB) + ccache → **~250 GB free**
      (workstation: `/mnt/hdd` 3.6 TB free; `/home` 144 GiB, `/` 184 GiB)
- [ ] device tree: copy `device/xiaomi/laurel_sprout` → `laurus`; set
      `ro.product.vendor.device=laurus`, vendor props, audio overlay; kernel config
      `vendor/laurus.config`
- [ ] build `systemimage` + `vendorimage`; modules signed by the build key
- [ ] flash/test as in Phase 2/3

## Debugging matrix

| stage | source |
|---|---|
| bootloader | `logfs`/`logdump`/`minidump` partitions; UART (unverified whether retail XBL/ABL print) |
| kernel/init | pstore `console-ramoops-0`, `dmesg-ramoops-0`; UART only with the debug kernel (stock/LOS configs lack the GENI console) |
| bootloop | TWRP on `recovery` (adb, `/sys/fs/pstore`); LOS init falls back to recovery |
| userspace | `adb logcat -b all -d`, `adb shell dmesg` |
| hard failure | EDL TP4728/TP4729 (9008), laurus fastboot ROM + MiFlash |

Key strings: `CANNOT LINK`, `VNDK`, `vintf`, `avc: denied`, `init:`, `Failed to mount /data`.

UART: TP4711 (SoC TX/GPIO16) → adapter RX, TP4719 → GND, 1.8 V (inferred), 115200 8N1.
TP4712 (SoC RX/GPIO17) is on the opposite face, inside the SH4716 outline — not needed for logs. See notes §13.
EDL: short TP4728/TP4729, plug USB → `05c6:9008` — see notes §12.

## Rollback ladder

1. `fastboot flash <part> /mnt/hdd/laurus/project-data/backups/2026-10-25/<part>.img` (boot/vendor/system/dtbo/vbmeta)
2. Full firmware restore: laurus V10.2.13.0 fastboot ROM with `flash_all_except_data_storage.sh`
   or `flash_all.sh` (never `flash_all_lock.sh` / MiFlash "clean all and lock")
3. Restore GPT only if it is damaged: write **only** the GPT ranges (sda: `count=6 seek=0` from
   `gpt_primary.bin`, and 33 blocks at LBA 30119903 from `gpt/sda_tail.bin`) — notes §5.1.
   Never write a whole 1 MiB `*_head.bin`/`*_tail.bin` back.
4. EDL + laurus fastboot ROM (last resort; needs Mi authorization)

## Facts that must not be lost

- A3 and CC9e are the **same hardware** (S88512AA1); camera/sensor configs are shared
  (`laurus_*` even in the A3 vendor). Audio: both use the `trinket-qrd-snd-card` card →
  `mixer_paths_qrd.xml` + `acdbdata/QRD/`; only the QRD calibration data differs (CC9e vs
  A3). The earlier "laurus = IDP" claim was wrong: `acdbdata/IDP/` is never loaded.
- `vbmeta` flags **0x3** disable verity; the live vbmeta is stock with only the flags byte
  patched (invalid signature, accepted because unlocked). A stock vbmeta is untested but would
  fail: system/vendor/dtbo no longer match their descriptors.
- Module signing keys are per kernel build (stock: SHA-512, LOS: SHA-256, our debug kernel: off);
  each module set loads only into its own kernel.
- GPT uses **4K logical blocks** (header at offset 4096; backup header in the last block, backup
  entries at last − 32).
- The CC9e is **A-only**; the A3/LOS images are A/B (`slotselect`), hence the boot repack.

## References

- `README.md` — current stack, root/hiding, kernel branches and safety.
- `kernel/README.md` — the working BakaSU main/SUSFS kernel build recipe + dead ends.
- `/mnt/hdd/laurus/kernel/SUSFS-PORT.md` — the SUSFS 4.14 port record (BakaSU main 35252 update section).
- `notes/cc9e-notes.md`, `notes/hardware.md`, `misc/schematic/` (S88512AA1 schematic,
  UART/EDL/JTAG), `misc/vendor_compare/`, `logs/`, `artifacts/`, `firmware/`, `tools/`.
