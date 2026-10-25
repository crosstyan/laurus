# LOS upgrade without wiping userdata (laurus, A-only)

You are not on an A-only LOS build: the installed system is the **laurel_sprout (A3) A/B
nightly**, cross-flashed onto the CC9e's A-only partitions. Current state (2026-10-25):
LOS 24.0 nightly `20261020`, GApps, BakaSU rc3 + SUSFS, custom boot, grafted A3 vendor.

Why the **LineageOS Updater cannot do it**:

- The build advertises `ro.build.ab_update=true` (it is an A/B payload build), but this phone
  has **no slots**: `ro.boot.slot_suffix` is empty and `/dev/block/by-name` has plain
  `boot`, `system`, `vendor`, `dtbo` (no `_a`/`_b`). `update_engine` has no inactive slot to
  write.
- Recovery is TWRP 3.3.1, not LOS recovery; the official zip is a payload OTA, not a
  sideloadable package. Do **not** accept an Updater OTA.

## Manual dirty upgrade (recommended)

1. Download the next `lineage-24.0-*-nightly-laurel_sprout-signed.zip`, verify its sha256.
2. Extract the payload:
   ```sh
   /mnt/hdd/laurus/downloads/tools/payload-dumper-go -o /mnt/hdd/laurus/graft/los-next ZIP
   ```
   The payload contains `abl xbl tz modem dsp boot dtbo system vendor vbmeta …`.
   **Only system/vendor/boot/dtbo are candidates** — never the firmware partitions.
3. Rebuild the system image with GApps (they live in `/system` and are lost on replacing it):
   ```sh
   python3 tools/install_gapps_offline.py \
     --system los-next/system.img \
     --gapps /mnt/hdd/laurus/downloads/gapps/MindTheGapps-17.0.0-arm64-*.zip \
     --out out/system-next-gapps.img --size 5120M
   ```
   This grows the fs to the 5 GiB partition, copies GApps, fixes modes/labels, erases the
   stale AVB footer (fine: the boot fstabs have `avb` stripped).
4. Compare the vendor image (hash against the installed 20261020 vendor). In practice
   nightlies within LOS 24 do **not** change vendor: the blobs stay pinned to the A3
   `V12.0.26.0` firmware, so this is almost always a no-op and the upgrade is system-only.
   Keep `vendor-laurus-fix10` (and the custom boot) untouched — no module re-signing, no
   keymaster/FBE risk. Re-graft only if the hash actually changed (new Android branch or a
   deliberate blob update):
     ```sh
     python3 tools/graft_vendor.py --los los-next/vendor.img \
       --cc9e <CC9e A9 vendor.img> \
       --modules /mnt/hdd/laurus/kernel/out-susfs-perf/modules \
       --out out/vendor-next-graft.img
     ```
     (erases the AVB footer and grafts CC9e QRD ACDB + `adsp_avs_config.acdb` + this
     kernel's 3 modules. It does **not** strip `slotselect` from `/etc/fstab.qcom` or
     remove the boot-control HAL; apply the `vendor-laurus-fix1` edits, or start from an
     already-fixed vendor image. **Do not use raw LOS as the base for a module-only
     update**: fix9 did and vold hung on `boot-service.qti`/slotselect; fix10 was built from
     fix8 + the new modules. The tool now accepts a footerless grafted base.
     See `notes/bringup-2026-10-25.md`.)
5. Boot/kernel: keep the current custom boot — a system-only nightly does not require a
   kernel change, and the boot/vendor pair stays matched. Only if you deliberately want the
   new LOS kernel (or a system change requires it) do you rebuild `susfs-perf`, repack with
   enforcing, rebuild the modules, and flash **boot+vendor as a pair**.
6. Flash only what changed; do not erase anything:
   ```sh
   fastboot flash system out/system-next-gapps.img
   fastboot flash vendor out/vendor-next-graft.img   # only if changed
   fastboot flash boot … / fastboot flash dtbo …     # only if changed
   ```
   **Never** `fastboot -w`; never erase `userdata`/`metadata`; never flash `vbmeta` (keep the
   stock flags 0x3) or any firmware partition.
7. Reboot (first boot may take longer), then verify: data intact, GApps, root (`su`), SUSFS,
   camera/audio, Wi-Fi/Clash, Ruru.

## Caveats

- Vendor security patch is **2022-08-01** (`ro.vendor.build.security_patch`), from Xiaomi's
  last A3 blobs `V12.0.26.0.RFQMIXM` (Android 11); the LOS vendor image's 2026 build date does
  not change that (system SPL is 2026-10-01, kernel 4.14.357-openela). Trust's "Vendor: Out of
  date" is expected and cannot be fixed without new closed blobs.
- Keep system and vendor matched (VNDK/HAL). Because vendor is normally unchanged, a
  system-only nightly is the low-risk path: userdata, FBE and the custom boot/vendor pair are
  untouched. A vendor swap would change keymaster blobs (the one thing that could affect FBE
  decryption) — avoid it unless truly required, and take a fresh userdata backup first. A full
  backup from 2026-10-25 already exists.
- GApps data (`/data`) survives; the GApps *system files* must be re-applied to each new
  system image.
- The custom kernel's vendor modules are signed per build; never mix a boot from one build
  with vendor modules from another.
- Downgrades are unsupported; stay within LOS 24 until a deliberate full migration.
- As of 2026-10-25 the only laurel_sprout 24.0 build in the LineageOS API is the installed
  `20261020`; this procedure is for the next nightly.

## Alternatives

- TWRP can write a raw system image (`Install → Install Image → system`), but fastboot is the
  established, safer path here.
- Building an A-only block-based OTA zip is possible but more work than swapping images, and
  the recovery is TWRP anyway.
