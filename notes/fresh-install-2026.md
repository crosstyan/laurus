# Flashing a CC9e in 2026 — clean install, and why the 2019 trick worked

The 2019 XDA guide ([How to Flash BeastROM to Mi CC9e](https://xdaforums.com/t/guide-rom-how-to-flash-beastrom-to-mi-cc9e.3970925/))
is still the clearest short explanation of the cross-flash. It is also wrong in one important
place, silent on three gates, and its download links are the kind that rot. This is what I would
write now, for the current LineageOS 24 state. Sources: that thread, the Mac's omp playbook
`~/.omp/agent/managed-skills/xiaomi-laurus-crossflash/`, and this repo's corrected notes.

## The 2019 recipe, audited

| 2019 step | 2026 verdict |
|---|---|
| “laurus **MUST** flash an **A/B image**, not A-only” | **Misleading.** The file is a raw ext4 **system-as-root** image. A/B is the update-slot scheme, not an image format. What matters is that the system image matches the installed vendor's VNDK/Android version. |
| “flash `system.img` **ONLY**” | **Correct** for an Android 9 system-only cross-flash. Keep the laurus `boot`, `vendor`, `dtbo` as the base; only `/system` is replaced (Magisk later patches the boot ramdisk in place). |
| “reboot to TWRP, wipe data” | **Incomplete.** Format data, and on LOS 24 also format `/metadata` ext4. “Wipe” in TWRP may leave encryption in place. |
| “flash vbmeta with `--disable-verity --disable-verification`” | **Correct**, and it is the first gate. Use the **laurus** vbmeta, never the A3 one. Flags `0x3`. |
| “you **HAVE TO** flash Magisk, or it bootloops” | **True in 2019, false now.** Magisk 19.4 patched the boot fstab **when present** (`verify`/`forceencrypt`); on this phone's stock boot there is no ramdisk fstab, so the vbmeta flags were the actual gate. Magisk 24303+/v24.3 removed the fstab patch from the 2SI path; newer Magisk is root only. Patch the fstab (if any) and vbmeta yourself. |
| “flash `misc.bin` so Xiaomi stops restoring stock recovery” | **Workaround.** `misc` is the bootloader control block (BCB). Boot straight into TWRP after flashing it; the exact bytes of BeastROM's `misc.bin` are not verified here. |
| Drive/Lanzous links, no hashes, no rollback | **Do not copy.** Pin sha256s, use mirrors/archives, and document the rollback ladder. |

## Why the 2019 trick worked (mechanism)

### 1. `system.img` is just a filesystem

The A3 fastboot ROM's `system.img` is a plain ext4 image with `init` at its root (system-as-root,
mandatory for devices launched with Android 9). The CC9e's `system` partition is a plain 5 GiB
ext4 partition. `fastboot flash system` writes the image; there is no slot suffix in the file.

`slotselect` is a **fstab flag**, not an image property. The laurus boot's first-stage fstab points
`/system` at `/dev/block/by-name/system`, so the A3 image mounts. An A/B OTA zip is not flashable
here, but an A/B **fastboot ROM's** `system.img` is just a filesystem image — that is the whole
“A/B trick”. The project's own LOS 24 install proves the reverse: A/B LOS images work on this
A-only phone after the boot/vendor fstabs are stripped of `slotselect`/`avb`.

### 2. The system ↔ vendor ABI matched (in 2019)

Project Treble splits the framework (`/system`) from the device-specific userspace (`/vendor`).
In 2019 the laurus vendor was Android 9 / VNDK 28, and the A3 Android 9 system was also VNDK 28;
the HAL clients and interfaces matched. The A3 and CC9e share the SoC, board, kernel, panel,
cameras and sensors, so the A3 framework runs on the laurus vendor.

Keeping the laurus `boot`, `vendor` and `dtbo` also kept the laurus firmware, modem, touch,
display and calibration native. Only the framework and apps changed. This is why the guide says
to flash `system.img` **only**; flashing the A3 `boot`/`vendor`/`dtbo`/`vbmeta` breaks the match.

The guide's own note that the **stock A3** system “boots, but screen blinks and sticks on the
welcome page” is a reminder that “same SoC” is necessary, not sufficient: the system's device
overlays/configs can still disagree with the vendor. BeastROM 1.6 happened to work; stock A3
did not.

### 3. AVB is the first gate

The laurus `vbmeta` contains AVB descriptors (hashes) for the original `boot`, `system`, `vendor`,
`dtbo`. Replacing `system` invalidates the hash. With verification enabled, the bootloader
refuses to boot (or dm-verity fails) — the guide's “stuck on Logo”.

`fastboot --disable-verity --disable-verification flash vbmeta laurus-vbmeta.img` writes the
**laurus** vbmeta with flags `0x3`:
bit 0 = hashtree disabled, bit 1 = verification disabled. The image keeps the laurus keys and
descriptors; the bootloader is unlocked, so it accepts the modified flags. Never flash the A3
vbmeta (wrong keys/descriptors), and do not relock.

### 4. dm-verity / force-encrypt is the second gate

Even with AVB off, Android's first-stage init reads the boot ramdisk's fstab. If `verify` is
present it sets up dm-verity for the modified system (hash mismatch → loop); if `forceencrypt`
is present it tries to encrypt the old `/data` (which was encrypted with the previous system's
keys → loop). That is the guide's “stuck on boot animation”.

Magisk's boot patch removed the `verify`/`forceencrypt` flags **when the boot image had an
fstab**. On this phone's original boot the ramdisk has no fstab (the fstab is in vendor), so
the vbmeta flags were the verity gate; the guide's Magisk step is specific to its boot image.
The 2026 equivalent is a repacked boot whose fstabs have `avb`/`verify` stripped (if any),
plus formatting `/data`; root is a separate decision. The project's
`tools/repack_los_boot.py` does the fstab edits, and the LOS 24 vendor fstab is patched too.
Newer Magisk (24303+/v24.3) no longer patches the fstab in the 2SI path, so **do not rely on
it**; patch the fstab and the vbmeta explicitly. Details: `notes/avb-vbmeta.md`.

### 5. `misc` is the recovery-restore workaround

`misc` holds the Android bootloader control block (`boot-recovery`, status, recovery message).
Xiaomi's stock system/OTA can restore the stock recovery on the next boot; a stale BCB can also
send the phone to recovery. Flashing a known `misc` image clears/sets that state, and booting
straight into TWRP (Volume Up + Power) means the stock system never runs first. The exact content
of BeastROM's `misc.bin` was not verified; the laurus stock `misc.img` is all zeros. Treat the
step as a workaround, not a rule.

## Why the 2019 recipe is not enough in 2026

- **The ABI no longer matches.** LOS 24 is Android 17; the laurus A9 vendor is VNDK 28. A
  system-only swap is expected to fail at the VNDK/LLNDK boundary. The working path is the full
  A3 stack: LOS `system` + LOS `vendor` (VNDK 30) + LOS `boot` + LOS `dtbo`; the laurus firmware
  stays untouched.
- **The A3 vendor is A/B.** On this A-only phone: strip `slotselect`/`avb` from both the boot
  ramdisk fstabs and `/vendor/etc/fstab.qcom`; remove the A/B boot-control HAL
  (`android.hardware.boot-service.qti` rc + VINTF); otherwise `vold` waits forever.
- **`/metadata` must be ext4.** Erasing it is not enough. The vendor fstab mounts `/metadata` in
  first stage, and `/data` uses `keydirectory=/metadata/vold/metadata_encryption`. Format it.
- **The kernel window is 52 MiB, confirmed from the ABL.** IDA decompiled
  `UpdateBootParams`/`BootLinux` from the compressed ABL PE (`notes/abl-bootlinux.md`). The
  64-bit fallback is `KernelLoadAddr = BaseMemory | 0x80000`,
  `KernelEndAddr = BaseMemory + 0x3400000`; the 32-bit path is `0x8000`/`0x3200000` (50 MiB).
  The UEFI-variable path uses `KernelBaseAddr + KernelSize`; the known-good 51.957 MiB image
  ends at `0x43475000`, consistent with `0x43480000` (52 MiB from the load address). The
  debug 61.84 MiB image ends at `0x43e57000` (9.84 MiB over) and resets. The ABL's
  `KernelSizeActual` is the **decompressed blob** (48.33 MiB), not `image_size`; the actual
  headroom is ~3.6 MiB, while the `image_size` margin is only 44–80 KiB. Repack the A3 boot
  image v2→v1; aim ≤48 MiB for new builds. This is not a standard: the boot partition is
  64 MiB, but the ABL offsets/PCDs are device-specific.
  - **Other devices, for context:** `boot` partitions are commonly 32 MiB (older), 64 MiB
    (most 2019 A-only), or 96/128 MiB (A/B, or separate `vendor_boot`). Production 4.14/4.19
    kernels are usually 20–40 MiB of `image_size`; GKI 5.10/5.15 are ~20–35 MiB; debug
    builds can be 50–70 MiB. The limit is the bootloader's load window or partition size,
    not a universal kernel size. Other Qualcomm/Samsung/MediaTek devices use 16/32/64 MiB
    gaps or separate `vendor_boot` partitions; do not copy 52 MiB to another model.
- **Boot and vendor are a module-signing pair.** The three vendor `.ko` files load only into the
  kernel that built them; never mix a boot from one build with a vendor from another.
- **Root/hiding moved on.** Magisk 19.4 is not the 2026 answer: BakaSU + SUSFS is. SELinux
  enforcing, Trust, cmdline/uname spoofing, and Ruru are separate verification steps.
- **GApps moved on.** MindTheGapps 17 is installed offline into the system image; the 2019 TWRP
  is too old to run the Android 17 installer.
- **Tools changed.** This abl has no `fastboot boot`; every test flashes. Fastboot works from the
  Mac, not the Linux workstation's xHCI. Use a USB 2.0 port if the link flaps.

## The 2026 tutorial (outline with the current commands)

### 0. Identify before writing

```sh
fastboot getvar product          # laurus
fastboot getvar unlocked         # yes
fastboot getvar anti             # 1; do not cross it
fastboot getvar current-slot     # FAILED: this is A-only
adb shell getprop ro.product.device ro.product.vendor.device
adb shell getprop ro.vendor.build.version.sdk
```

If `product` is not `laurus`, stop. Do not flash a laurus ROM to an A3 or vice versa.

### 1. Back up

At minimum: GPT (4K blocks!), `boot`, `dtbo`, `vbmeta`, `vendor`, `system`, `recovery`,
`persist`, `modem`, `misc`, and `/data` if it matters. Verify sha256 on both sides. The project's
2026-10-25 set is the reference: `/mnt/hdd/laurus/project-data/backups/2026-10-25/`.

### 2. Choose a baseline

- **Already-unlocked CC9e running MIUI** (the realistic second-hand case; no 168-hour wait):
  do not relock. Identify the firmware first:
  ```sh
  fastboot getvar product unlocked anti
  adb shell getprop ro.build.version.release
  adb shell getprop ro.miui.ui.version.name
  adb shell getprop ro.vendor.build.version.sdk
  ```
  Back up the GPT and partitions, then pick one:
  - **laurus A9 V10.2.13.0** — the project's tested baseline. Flash the official laurus A9
    fastboot ROM with `flash_all_except_data_storage.sh` (never `flash_all_lock.sh`); it
    restores the matching firmware, vendor, boot, recovery and vbmeta. Re-flash TWRP and
    re-apply vbmeta flags `0x3`.
  - **Newer MIUI (A10/A11)** — do not downgrade blindly. Either keep the current firmware and
    flash the LOS images (plausible, but not the project's tested firmware), or flash the
    matching laurus A10 `V12.5.5.0` ROM (`CURRENT_ANTI_VER=1`) first. Check `fastboot getvar
    anti` against the ROM's `CURRENT_ANTI_VER`; if the device's anti is greater, stop.
  MIUI may restore stock recovery: boot TWRP immediately after flashing it. Format `/data`;
  MIUI's encryption will not open under LOS.
- **Known-good current phone:** skip the stock ROM; the firmware is already the laurus A9 one.
  Go to the LOS images.

### 3. Prepare the images (LOS 24 path)

- Extract the A3 payload; use only `system`, `vendor`, `boot`, `dtbo`. Never the A3 firmware.
- Boot: repack v2→v1, strip `slotselect`/`avb` from the ramdisk fstabs, check
  `image_size` ≤ 52 MiB (0x3400000). For bring-up, `--permissive` + `--debuggable`; for
  daily, enforcing.
- Vendor: graft CC9e QRD audio calibration (`acdbdata/QRD/*` + `adsp_avs_config.acdb`) and the
  kernel's three modules; strip `slotselect` from `/etc/fstab.qcom`; remove the boot-control
  HAL; erase the stale AVB footer. Note: the old omp skill says “laurus = IDP”; that was
  disproven — both phones use the QRD card, and `acdbdata/IDP/` is never loaded.
- System: install GApps offline into the 5 GiB image; sparse it if the host fastboot refuses the
  raw 3 GiB file.

### 4. Flash

```sh
fastboot flash boot   boot-<kernel>.img       # header v1, ≤51.96 proven (52 MiB hypothesis), vendor pair
fastboot flash dtbo   dtbo.img
fastboot flash vendor vendor-laurus-fixN.img  # same build's modules + fstab/HAL fixes
fastboot flash system system-gapps.sparse.img
fastboot erase userdata                       # LOS formats f2fs itself
fastboot format:ext4 metadata                 # never just erase it
fastboot reboot
```

The `metadata type is raw, but ext4 was requested` warning is expected; fastboot runs `mke2fs`
and writes a valid 16 MiB ext4 image. The `Did you mean to fastboot format this ext4 partition?`
warning on `erase userdata` is also expected; LOS formats `/data` as f2fs.

### 5. First boot

Allow ~2.5 minutes. If there is no USB, wait for boot completion, then use TWRP adb and read
`/sys/fs/pstore/console-ramoops-0`. If the screen is stuck at the “unlocked”/Mi logo with empty
pstore, the kernel never ran: check the kernel `image_size` and boot header.

### 6. Verify

`sys.boot_completed=1`, `uname -r`, `/data` f2fs + FBE, cameras/audio/sensors/Wi-Fi/BT/
fingerprint, root (`adb shell su -c id`), Trust/SELinux, modules. Then install the manager,
GApps data, and the hiding config.

### 7. Rollback

Partition images → official laurus fastboot ROM → GPT ranges → EDL (TP4728/TP4729). Never lock.
Never restore another device's `persist`.

## If you want to “start fresh”

- **Already-unlocked CC9e running MIUI:** see “Choose a baseline”. Back up, keep the
  bootloader unlocked, pick the A9 or the matching newer laurus ROM, then TWRP + LOS. Never
  flash the A3 ROM or A3 firmware.
- **Clean reinstall of LOS on the current phone:** no stock ROM needed if the firmware is
  already correct. Flash the four images, `erase userdata`, `format:ext4 metadata`, reboot.
- **Keep data:** do **not** start fresh; use `notes/los-upgrade.md` (system-only nightly swap).
- **Return to stock:** laurus fastboot ROM; never relock; don't restore `persist` from another
  unit.
- **Factory reset from LOS:** Settings → System → Reset options. If it fails, the fastboot
  pair (`erase userdata` + `format:ext4 metadata`) is the fallback.
- **Repartition?** No. The GPT is fine; there is no `super` partition, and changing it adds
  brick risk for no gain.

## What not to write (the 2019 mistakes)

- “A/B image” as the reason it works. Say “raw ext4 system-as-root image whose VNDK matches the
  vendor”.
- “Magisk is mandatory.” Say “patch the fstab and vbmeta explicitly; old Magisk did it, newer
  Magisk does not”.
- “Wipe data.” Say “format data, and format `/metadata` ext4 on modern builds”.
- Dead cloud links and no hashes. Pin sha256, keep a local mirror, and document rollback.
- No firmware warning. The single most dangerous step is flashing the other phone's firmware.

Details of the two failed first boots and the exact evidence: `notes/bringup-2026-10-25.md`.
No-wipe LOS updates: `notes/los-upgrade.md`. Full GPT table: `notes/partition-table.md`.
AVB/vbmeta/dm-verity/Magisk details: `notes/avb-vbmeta.md`. Current flashed stack:
`README.md`.
