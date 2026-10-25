# CC9e (laurus) — cross-flash notes

Date: 2026-10-25. Device serial: `<redacted-device-serial>`.
Claims re-validated 2026-10-24 (workstation clock) against local evidence; corrections are
marked *(corrected)*.

## 1. What this phone actually is

| layer | value |
|---|---|
| Hardware | Xiaomi **Mi CC9e (laurus)**, `ro.product.cert=M1906F9SC`, `ro.boot.hwc=CN`, `ro.boot.product.hardware.sku=394`, board `S88512AA1`, QRD, `qcom,board-id` 0x0b |
| SoC | SM6125 TRINKET (`qcom,msm-id` 0x18a), 128 GB UFS (`4804000.ufshc`, six LUNs = 127.95 GB). RAM: 6 GB SKU per spec; logs show only `Memory limit set/overridden to 5068MB`, 4,846,240 K usable *(corrected: "6 GB" is not in the logs)* |
| Panel | `dsi_s6e8fco_samsung_hdp_video_display` 720x1560 (the A3 dtbo has the same node; "same panel as the A3" is inferred) |
| system | `Xiaomi/laurel_sprout/laurel_sprout:9/PKQ1.190416.001/V10.3.4.0.PFQMIXM` (Mi A3 Android One, 2019-08-15, sec patch 2019-08-05) |
| vendor | `Xiaomi/laurus/laurus:9/PKQ1.190416.001/V10.2.13.0.PFMCNXM` (CC9e MIUI 10, 2019-08-29, sec patch 2018-08-05), VNDK 28, VINTF target-level 3 |
| boot kernel | `4.14.98-perf+ #1 SMP PREEMPT Thu Aug 29 23:21:41 CST 2019`, builder `c3-miui-ota-bd124.bj`, clang 6.0.9 (`bootbak` holds a different 4.14.98 build, `cibuild@cibuild`, 2019-06-12) |
| dtbo | 1 DTB, `model = "QRD"`, `compatible = "qcom,trinket-qrd"`, panel `s6e8fco_samsung_hdp_video` |
| recovery | wzsx150 TWRP 3.3.1 for CC9e (Android 9 based, `omni_xiaomiCC9e`) |
| bootloader | unlocked (`ro.boot.verifiedbootstate=orange`, `flash.locked=0`) |
| root | Magisk 27.0 (R), 11 modules (riru-core/sui/storage_redirect/ifw_enhance/location_report_enabler/ibr, notocjk, blobmoji, quickstepswitcher, nfsinjector, swift_installer) |
| baseband | `MPSS.AT.4.3.1.c1-00015-NICOBAR_GEN_PACK-1.217874.1_V014` |

So: **A3 system + CC9e kernel/vendor/dtbo**. The "bootimage fingerprint" saying `laurel_sprout` comes from `/system/etc/prop.default`, not the boot ramdisk.

## 2. AVB state

Dumped live `vbmeta` (sde17, 64 KiB):

```
magic AVB0, ver 1.0, auth 320, aux 2048, rollback 0
flags = 0x3  → HASHTREE_DISABLED | VERIFICATION_DISABLED   (byte 0x78, big-endian u32)
```

Full header/descriptor layout, dm-verity and Magisk/fstab gates: `notes/avb-vbmeta.md`.

*(corrected)* It is a **signed stock vbmeta with only the flags byte patched**, not re-signed:
`avbtool verify_image` fails ("Signature check failed"); zeroing the flags on a copy makes it verify.
That works only because the bootloader is unlocked. The effect equals
`fastboot --disable-verity --disable-verification flash vbmeta ...`.
`vbmetabak` is a *different* stock vbmeta (other key, other digests, flags 0), not a backup of this one.

What happens with a stock vbmeta is **untested**. Offline evidence: system, vendor and dtbo no
longer match their signed AVB descriptors (hashtree/digest mismatch), so verity would fail.
"Flags 0x3 are the only reason it boots" is overstated.

The boot image is Magisk-patched (ramdisk = `init` + `overlay.d/` + `.backup/{init.xz,.magisk,.rmlist}`
+ `magisk32/64/stub.xz`). *(corrected)* Magisk does **not** set any boot-side verity flag here: the
ramdisk has no fstab, the appended DTBs carry no fstab/avb entries, and the vendor fstab still has
`wait,avb` for `/`. At runtime only the vbmeta flags disable verity.

## 3. Why the cross-flash works

1. Same SoC, board and board-id QRD DTB on both phones *(corrected: "kernel is literally interchangeable" was untested)*.
2. Both are Android 9 SAR devices → the A3 `system.img` (plain ext4, init at root) mounts fine.
3. Treble: system ↔ vendor split. The device-specific userspace lives in the **laurus vendor**;
   kernel, dtbo, modem/dsp/bluetooth firmware and persist are device-specific too *(corrected: not "all" in vendor)*.
4. AVB/verity is the gate → disabled via the vbmeta flags.
5. *(corrected)* `/vendor/etc/camera/laurus_{imx582,imx586,s5kgd1,ov13855,ov02a10,gc2375,s5k4h7}_*`
   (+ `_india`, `_global`, `_factory`) are **not** a CC9e-vs-A3 difference: the A3 vendor carries the
   same `laurus_*` set, and `camera_config.xml` differs only by one commented-out OV13855 block.
   The variants are camera batches/tuning. See `notes/hardware.md`.

Real platform differences between the two vendors/DTs (validation 2026-10-24):
- **A/B vs A-only**: the A3 fstab uses `slotselect,avb,first_stage_mount`; the CC9e is non-A/B with a
  `recovery` partition. `tools/repack_los_boot.py` strips `slotselect`/`avb` for this reason.
- **CC9e-only DT nodes** missing from the A3 DT: `xiaomi,simtray-status` (GPIO 98), `xiaomi_touch`,
  FT3518 tuning (`fts,touch-tolerance-*`, `fts,edgefilter-*`), and the CC9e thermal cooling maps
  (`pmi632-ibat/vbat-lvl*`; the A3 uses `pmi632-bcl-lvl*`). The camera nodes are the same.
- **Audio calibration data** (`acdbdata/QRD/*`); see `misc/vendor_compare/SOURCES.md` and `tools/graft_vendor.py`.

## 4. Anti-brick rules (ordered)

1. **Never relock the bootloader.** Locking with a non-stock system = hang / fastboot loop. Stay `orange`.
   This includes MiFlash "clean all **and lock**" and `flash_all_lock.sh`: use "clean all" /
   `flash_all.sh` / `flash_all_except_data_storage.sh` only.
2. **Never flash bootloader partitions**: `abl`, `ablbak`, `xbl`, `xblbak`, `xbl_config*`, `tz`, `tzbak`, `hyp*`, `devcfg*`, `cmnlib*`, `keymaster*`, `rpm*`, `modem`, `modembak`, `dsp*`, `mdtp*`, `bluetooth*`, `qupfw*`, `uefisecapp*`, `imagefv*`. Full OEM restore only.
   The LOS 24 payload contains A3 versions of 16 of these (abl, xbl, xbl_config, tz, hyp, rpm, devcfg,
   keymaster, cmnlib*, qupfw, storsec, uefisecapp, imagefv, modem, dsp, bluetooth): extract and flash
   only `system vendor boot dtbo`.
3. **Restore with a CC9e (laurus) fastboot ROM, never the A3 ROM.** Both are local and verified:
   - `/mnt/hdd/laurus/downloads/laurus_images_V10.2.13.0.PFMCNXM_20190830.0000.00_9.0_cn_fc9f51f46d.tgz`
     (extracted in `rom-a9/`): its firmware is **byte-identical to the phone's** (abl, tz, hyp, rpm,
     devcfg, keymaster, cmnlib*, bluetooth, modem, xbl, xbl_config) — the matching full restore.
   - `/mnt/hdd/laurus/downloads/laurus_images_V12.5.5.0.QFMCNXM_20211122.0000.00_10.0_cn_fc0291dab7.tgz`
     (Android 10, `CURRENT_ANTI_VER=1`): would *upgrade* the firmware; not planned.
4. **Back up small critical partitions** + GPT. Done: `backups/2026-10-25/` (25 images + sda GPT) and the
   full dump `/mnt/hdd/laurus/full-backup-2026-10-25/` (all 83 by-name partitions except userdata, all 6 LUN GPTs,
   userdata as tar).
5. ~~Test with `fastboot boot <img>` before `fastboot flash`.~~ *(corrected 2026-10-25)* This `abl`
   **does not support `fastboot boot`**: upload OK, then `FAILED (remote: 'unknown command')`. Every test
   means flashing `boot`; keep `backups/2026-10-25/boot.img` at hand.
   Fastboot USB also never enumerates on the Linux workstation (Intel 700-series xHCI; tried a USB 3
   port, a USB 2.0-only port and a hub, with replugs: no kernel USB event at all), while Android/adb
   works there. **Use the Mac (`ssh <lan-ip>`, `~/Projects/laurus`) for fastboot**; it reports
   `product: laurus`, `unlocked: yes`, `anti: 1`, no `current-slot`.
6. Freely flashable: `boot`, `dtbo`, `system`, `vendor`, `vbmeta`, `recovery`. Everything else recovery-only.
7. TWRP is on `recovery` (wzsx150 3.3.1, CC9e). It gives adb + `/sys/fs/pstore` after a bootloop;
   it cannot decrypt LOS 24 `/data`.
8. Keep the current **vbmeta (flags 0x3)**; do not flash a stock one while running a non-stock system.
9. **Never flash or sideload `firmware/CC9e安卓11底层.zip`**: its updater writes `modem`, `vbmeta`
   (flags **0x2**), `boot`, `dtbo` and `vendor` (see §9).

## 5. Useful commands

Dumping a partition *(corrected)*: `adb shell cat` — and `adb exec-out` through Magisk `su` — runs
through a pty that rewrites LF → CRLF and corrupts binaries. Write to a file with `dd`, then `adb pull`
(or stream with `stty -onlcr` + `nc`, as the dump scripts do):

```sh
adb shell 'su -c "dd if=/dev/block/by-name/boot of=/data/local/tmp/boot.img bs=4096"'
adb shell 'su -c "chmod 644 /data/local/tmp/boot.img"'
adb pull /data/local/tmp/boot.img .
```

Known casualties: `analysis/boot.img` and `analysis/boot2.img` are CRLF-corrupted copies (use
`analysis/boot_dd.img`); `artifacts/cc9e_dump_*/gpt_*.bin` are garbage (use `backups/` or `/mnt/hdd/…/gpt/`).

Partition table:

```sh
adb shell "cat /proc/partitions"
adb shell 'su -c "ls -l /dev/block/by-name/"'
```

Unpack boot header / kernel / ramdisk (Python):

```
magic ANDROID!, then <10I: kernel_size kernel_addr ramdisk_size ramdisk_addr
second_size second_addr tags_addr page_size header_version os_version
```

Parse vbmeta flags: offsets 4+4+4+8+8+4 (algorithm) + 10*8 (hash/signature/pubkey/pubkey-metadata/descriptors
offset+size) + 8 (rollback) = 120 = 0x78 → flags u32 (big-endian); bit0 = hashtree disabled, bit1 = verification disabled.

## 5.1 GPT layout (4K logical blocks!) — restore instructions *(corrected)*

The UFS uses 4096-byte logical blocks (sda = 30119936 blocks), so the GPT is **not** at 512-byte LBA1:

- protective MBR at offset 0 (0x55AA at 0x1FE); bytes 512–4095 of block 0 are zero padding
- GPT header at offset **4096** (LBA 1), partition entries from LBA 2
- backup header in the **last block** of the LUN; backup entries at **last − 32** (sda: LBA 30119903;
  32 entries × 128 B = 1 block; sde has 64 entries = 2 blocks)
- sda: usable LBA 6..30119902, header LBA 1 / backup 30119935

Backups:
- `backups/2026-10-25/gpt_primary.bin` / `gpt_backup.bin` = **LUN sda only**, 32 blocks each.
  `gpt_backup.bin` covers LBA 30119904–35 and **misses the backup-entries block** (30119903).
- `/mnt/hdd/laurus/full-backup-2026-10-25/gpt/<lun>_head.bin` / `_tail.bin` = first/last 1 MiB of **all six LUNs**.
  Never write a whole 1 MiB file back: the head overlaps live `persist` (sda LBA 6+), the tail overlaps
  the end of `userdata`.

Restore sda (only the GPT ranges; verified on a sparse 30119936-block test file):

```sh
# primary: LBA 0..5 (MBR + header + entries), first usable LBA is 6
dd if=gpt_primary.bin of=/dev/block/sda bs=4096 count=6 seek=0
# backup: entries (LBA 30119903) through header (30119935) = 33 blocks
dd if=/mnt/hdd/laurus/full-backup-2026-10-25/gpt/sda_tail.bin of=/dev/block/sda bs=4096 skip=223 seek=30119903 count=33
```

Other LUNs: compute the same two ranges from each LUN's own header (LBA 0 .. first_usable−1, and
last_usable+1 .. end); the per-LUN commands are in `/mnt/hdd/laurus/full-backup-2026-10-25/README.txt`.
File check: `grep -abo 'EFI PART'` finds 4096 in `gpt_primary.bin` and 126976 (block 31) in `gpt_backup.bin`.
After a restore, read the ranges back with `dd` and compare hashes.

## 6. Known partition map (important ones; sizes in MiB)

| name | dev | size |
|---|---|---|
| system | sda12 | 5120 MiB |
| userdata | sda14 | 110885 MiB = 108.3 GiB *(corrected from "110.9 GB")* |
| vendor | sde16 | 1024 MiB |
| cust | sda9 | 832 MiB |
| cache | sda11 | 512 MiB |
| catecontentfv | sde58 | 2088 MiB |
| modem / modembak | sde4 / sde24 | 200 MiB each |
| persist | sda2 | 32 MiB |
| boot / bootbak | sde11 / sde31 | 64 MiB each |
| dtbo / dtbobak | sde18 / sde37 | 24 MiB each |
| vbmeta / vbmetabak | sde17 / sde36 | 64 KiB each |
| recovery | sda10 | 64 MiB |
| metadata | sda13 | 16 MiB |

Full GPT table with all 84 by-name partitions, LBA ranges and attributes:
`notes/partition-table.md`. No `super` partition.

## 7. Kernel sources

| source | branch | notes |
|---|---|---|
| `MiCode/Xiaomi_Kernel_OpenSource` | `laurel-q-oss` (2020-01), `laurel-r-oss` (2021-06, 4.14.180) | official OSS, Mi A3 |
| same | `laurus-p-oss` (2019-07, "MI CC 9e and Mi A3 Android P"), `laurus-q-oss` (2021-02, 4.14.117) | official OSS, CC9e |
| `LineageOS/android_kernel_xiaomi_sm6125` | `lineage-24.0` (A17, 4.14.357-openela), also 22.2/23.0/23.1/23.2 | maintained, last push 2026-10-12; local full clone `/mnt/hdd/laurus/kernel/` |
| `anirudhkosgi/android-kernel-xiaomi-laurel_sprout` | lineage-18.1 | custom tree + AnyKernel3; stale (2023) |
| `Mi-A3-laurel-sprout/device_xiaomi_laurel_sprout-kernel` | A15 | prebuilt `Image`/`dtb.img`/`dtbo.img` only (not source) |

Device tree candidates:
- `LineageOS/android_device_xiaomi_laurel_sprout` (A3, LOS 24) — local full clone in `/mnt/hdd/laurus/build/device/xiaomi/`
- `N1709/device_xiaomi_laurus` branch `lineage-21.0` — "initial port", 0★, no `lineage.dependencies`; local clone in `/mnt/hdd/laurus/build/reference/`
- `AndroidBlobs/vendor_xiaomi_laurus` — blob dump, branches `laurus-user-9-…-V11.0.2.0…` and `laurus-user-10-…-V12.0.3.0…`

## 8. Experiment plan

Superseded by `PLAN.md`. (The old step "Magisk-patch the kernel, which sets verity flags" was wrong, see §2.)

**Result (2026-10-25):** done via PLAN.md Phase 3 — LOS 24 (Android 17) + CC9e audio graft
+ custom 4.14 kernel, plus MindTheGapps 17 and BakaSU v4.2.0-rc3 root (Shell root verified).
Phase 2 (system-only) skipped at the VNDK wall; Phase 4 (full laurus build) not needed. See
`README.md` for the current stack and `kernel/README.md` for the kernel build.

## 9. Local artifacts *(corrected)*

- `artifacts/cc9e_dump_pkq1_20261025_0123/` — getprop, `partitions_by_name.txt`; its `gpt_*.bin` are corrupt.
- `firmware/CC9e安卓11底层.zip` (424 MB): **an Android 11 community repack**, not a delta OTA and not
  Android 10. Signed with the AOSP test key; the `META-INF/com/android/metadata` (V12.0.4.0.QFMCNXM,
  sdk 29, `ota-type=BLOCK`) is stale leftover from an older package. Contents:
  - `vendor`: a **full** block image (`*.transfer.list` has only `new`/`zero`; `*.patch.dat` are empty) of the
    **Mi A3 Android 11 vendor** `Xiaomi/laurel_sprout/laurel_sprout:11/RKQ1.200903.002/V12.0.9.0.RFQMIXM`
    (sdk 30, VNDK 30).
  - `boot.img` 31 MB: kernel `4.14.180-perf-g18d36b38b14a` (`c4-xm-ota-bd036.bj`, clang 10.0.7, 2021-12-10),
    built from `laurel_sprout-r-stable-build` = the **Mi A3 Android 11 kernel**, not a laurus kernel. Its
    ramdisk (15.2 MB) is a **Magisk-patched TWRP 3.3.1 recovery** (`RECOVERYMODE=true`), not a MIUI ramdisk.
  - `dtbo.img`: 162,976 B, 1 entry (installed: 161,743 B), laurus-derived and functionally different (§10).
  - `modem.img` and `vbmeta.img` (**flags 0x2**); the updater-script flashes modem, vbmeta, boot, dtbo, vendor.
  - Extracted copies: `analysis/a11/{boot,dtbo}.img` (sha256-identical to the zip members).
- `analysis/` — boot/bootbak/dtbo/vbmeta dumps, extracted kernel/ramdisk (`boot.img`/`boot2.img` are CRLF-corrupt, use `boot_dd.img`).
- Newest **official laurus** kernel on disk: `4.14.117-perf-g4732215` (V12.5.5.0 ROM, 2021-11-21, `laurus-q-stable-build`).

## 10. Open questions → answers (2026-10-24)

- *Does the zip's boot.img boot the current system?* No: its ramdisk is TWRP (`RECOVERYMODE=true`), and
  the installed vendor's 40 `.ko` (vermagic `4.14.98-perf+`, signer `C2FB368AE959C656`) cannot load into
  that kernel (own per-build key, `MODULE_SIG_FORCE=y`).
- *Are the two dtbo images functionally different?* Yes: 1665-line `dtc` diff (thermal zones renamed,
  panel gains cmd/video `timing@1` + mode switch, `bl-default-level`); the zip dtbo is close to the
  V12.5.5.0 laurus dtbo (215 lines).
- *laurus vs laurel_sprout vendor diff?* Answered: cameras shared (§3.5), sensor JSONs byte-identical, audio
  only calibration data differs, DT/fstab differences listed in §3.
- *Adapt the A3 LOS 24 device tree to laurus?* Not needed — the LOS A3 images + graft route
  (PLAN.md Phase 3) succeeded, so no laurus device-tree build was done. A full laurus build
  stays an option (§11) only if a branded, reproducible image is later wanted.

## 11. Building the system yourself

- The device is **non-dynamic** (single `system` partition, 5120 MiB). Build `systemimage`
  with `PRODUCT_USE_DYNAMIC_PARTITIONS := false` and flash with
  `fastboot flash system system.img`. No GPT work needed.
- Base tree: `LineageOS/android_device_xiaomi_laurel_sprout` (branch `lineage-24.0`).
  For laurus: clone it, rename to `laurus`, run `extract-files.py` against a laurus
  fastboot ROM (V10.2.13.0 or V12.5.5.0, both local) to produce `vendor_xiaomi_laurus`, and use
  `LineageOS/android_kernel_xiaomi_sm6125` lineage-24.0.
- Kernel configs are embedded (IKCONFIG) in every kernel Image on disk; extract offline
  (`IKCFG_ST` marker) rather than from `/proc/config.gz`.
- Build host: `repo` ~120 GB + `out` ~60 GB + ccache → 250 GB free, 16+ GB RAM.
  Workstation: `/mnt/hdd` has 3.6 TB free. The Mac is arm64 (no).
- Installed vendor is **A9, VNDK 28** *(corrected from "A10 / VNDK 29")*; Android 17 no longer supports it,
  so a system-only swap is expected to fail (VNDK/LLNDK, sepolicy mapping, VINTF).
- Flash/rollback: `fastboot flash system system.img` / restore `backups/2026-10-25/system.img`;
  keep vbmeta at flags 0x3.

## 12. EDL / 9008 test points (schematic-confirmed)

Source: leaked `Xiaomi Mi A3 (laurel) & Mi CC9e (laurus) Schematic.rar` (S88512AA1 board),
copies in `misc/schematic/` (`schematic_S88512AA1.PDF` 58 pages, `board_top_bottom_artfilm.pdf`,
plus crops 01-06; 05/06 are JPEG despite `.png`). Test sheet = PDF page 33 (sheet 47 of 53; bracketed
net refs on the sheets are sheet numbers, not PDF pages).

```
TP4728 (1 mm) ── R4704 1K  ──> FORCED_USB_BOOT   (SoC GPIO_99, sampled by the PBL)
TP4729 (1 mm) ── R4703 10K ── VREG_L9A_1P8 (1.8 V)
```

*(corrected: FORCED_USB_BOOT is SoC GPIO_99, not a PMIC strap.)*
Short TP4728 <-> TP4729, then plug USB / power on -> QDLoader 9008 (`05c6:9008` per public sources,
not verifiable offline). The 10k + 1k series resistors make a tweezer short safe (~0.16 mA).

Location: main board, against the 40-pin LCD FPC connector J4001 (MIPI DSI0 + touch I2C); the two
1 mm pads sit diagonally beside a mounting screw boss in the open (unshielded) strip along the board edge.
Consistent with `misc/IMAGE 2026-10-25 02:19:30.jpg` and `06_photo_edl_pads.png`. The art film is board
rev `88512_1_20`, the schematic `1_21`.

Caveat: shorting only gets the 9008 port. Xiaomi still requires an authorized Mi account or a
patched firehose to actually flash; `fastboot oem edl` is the software shortcut when the
bootloader is alive.

## 13. UART (schematic-confirmed) *(location corrected)*

```
TP4711 (0.5 mm) ── R4701 1K ── DBG_UART_TX = GPIO_16   (SoC TX)
TP4712 (0.5 mm) ── R4702 1K ── DBG_UART_RX = GPIO_17   (SoC RX)
```

- QUPv3 wrapper 0, serial engine 4 @ `0x04a90000` (`qupv3_se4_2uart`, compatible `qcom,msm-geni-console`,
  pinctrl gpio16/17 function `qup04`) → `ttyMSM0` (`console=ttyMSM0,115200n8`,
  `earlycon=msm_geni_serial,0x4a90000` in the cmdline).
- **The stock kernel prints nothing here**: it has no GENI console driver (dmesg only registers `ttyHS0`
  at 4c90000). Kernel output needs the `laurus-debug.config` build (`SERIAL_MSM_GENI_CONSOLE=y`).
- Level: **1.8 V** (inferred from the PX_3 bank supply VREG_L9A_1P8), no level shifter, no pull-ups;
  115200 8N1 is the kernel's value, the bootloader's is unknown.
- Location (from the art film): **TP4711 (TX) is on the bottom film** beside the ESD diode D3701 and the
  earpiece spring contact J3705, with the "+" mark and the 1 mm GND pad **TP4719** right next to it.
  **TP4712 (RX) is on the opposite face**, inside the SH4716 shield-frame outline near R4701/U0501.
  For logs, TX + GND is enough. (J4103 nearby is the **front**-camera connector; SH4701 is the WCN can;
  U7001 the diversity antenna switch.) The 0.5 mm pad is ~1 mm from J3705/D3701 — careful with probes.
- Wiring: TP4711 (SoC TX) → adapter RX, TP4719 → adapter GND; only for console input: TP4712 (SoC RX) ← adapter TX.
- Unverified: whether retail XBL/ABL prints on UART (`xbl.img` contains `boot_logger_uart.c`,
  `UARTLogBufferSize = 0x19000`; enablement unknown).

JTAG on the same sheet: TP4727=TCK, TP4720=TDI, TP4721=TDO, TP4722=TMS, TP4723=SRST_N, TP4726=TRST_N
(C4701/C4702 10 nF to GND). These pads are **not labelled on either art-film layer** — they may not be fitted.

Same board family S88512AA1 for Mi A3 (laurel) and Mi CC9e (laurus), so the same TPs apply.

## 14. Root hiding: SUSFS + ReSuSFS (2026-10-25)

Live kernel: `4.14.357-openela-perf-susfs-g16b58dc8d946` — BakaSU **main 35252 / uapi 6**
**inline hooks** plus SUSFS **v2.3.0** non-GKI, forward-ported from `susfs4ksu`
`gki-android12-5.10` @ `5419f4e`. Flashed as the pair
`boot-susfs-main-perf-enforcing.img` (sha256 `41e1d8f5…`) + `vendor-laurus-fix10.img`
(sha256 `2d64bf3d…`). Manager 35252 shows SUSFS v2.3.0 / Inline.
`ksu_susfs show version` prints `v2.3.0`, variant `NON-GKI`, and six
`CONFIG_KSU_SUSFS_*` feature flags (ReSuSFS's `features: 7` line is `wc -l` counting the
trailing blank line). Preinit (main default-on) ran: `runner staged` then
`exec runner via /proc/self/fd/N`.

The public fork rewrote commit hashes for privacy: `laurus-susfs-main` is published at
`71adeaf` (the flashed `16b58dc` kernel code, plus the BakaSU source vendored in
`drivers/kernelsu`).

Config front-end: **ReSuSFS v26.10.23** (`ahmed-alnassif/ReSuSFS`), id `ReSuSFS`,
versionCode 22. It applies sus_paths (ROM/addon.d traces), mount hiding, sus_maps, kstat,
uname, props and settings at post-fs-data / boot-completed. Effective toggles:
`HIDE_SUS_MNTS_NON_SU=1`, `ENABLE_AVC_LOG_SPOOFING=1`, `ENABLE_LOG=0`.

Gotchas found the hard way:

- The installer's `customize.sh` asks "update the configs?" through `getevent` whenever
  `/data/adb/ReSuSFS` already exists; over adb no key is pressed and the install looks hung.
  Move that dir away (or keep it absent), feed stdin from `/dev/null`, and stream the output
  instead of piping it through `tail` (buffering hides the progress).
- The module updates `ksu_susfs` with BusyBox `wget`, which cannot fetch HTTPS through an HTTP
  proxy on this build (`wget: error getting response`; plain HTTP via the proxy works). With no
  network it fails DNS first. Workaround used: download on the host
  `…/susfs4ksu/-/raw/gki-android14-6.1/ksu_module_susfs/tools/ksu_susfs_arm64?ref_type=heads`
  (sha256 `21303cef99048d83bf689d33c3b474a872697c9c4583c45049c2b72a14c66de5`) and patch
  `customize.sh` to keep an existing binary instead of `update_susfs || exit 1`.
- `/data/adb/ksu/bin/ksu_susfs` is a **hardlink to `/data/adb/ksud`** (5.6 MB, has the newer
  `config` subcommands). Query it with `show version`; `version` is not a command. Keeping it
  is safe — ReSuSFS only uses the classic subcommands (`add_sus_path`, `set_uname`, …).
- Manager/driver version code is **`30000 + git commit count + 700`** (BakaSU
  `manager/build.gradle.kts`, `kernel/Kbuild`). rc3 = 4471 commits = **35171**;
  BakaSU `main` at `d5e9e025` = 4552 commits = **35252**. The main kernel is now built
  (`laurus-susfs-main` flashed tree `16b58dc`; published tip `71adeaf`, BakaSU main d5e9e025) and manager 35252 is installed;
  both report `35252/6` ("Working / Built-in"). The manager APK came from the main CI run
  `40109566037` via `nightly.link` (`Manager-release.zip`, arm64 APK sha256 `4fb6335a…`).
  `/data/adb/ksud` still prints `4.2.0-rc3 (uapi: 4)`; the manager uses its bundled
  `libksud.so` for uapi 6 and the old binary runs the ReSuSFS scripts, so this is expected.
  Keep manager and driver matched; a 35252 manager on a 35171 driver shows “Kernel update
  required”. Flash boot+vendor together.
- **Do not re-graft a module-only vendor update from raw LOS.** `tools/graft_vendor.py`
  replaces ACDB + modules only; it does not patch `/etc/fstab.qcom` or remove
  `/etc/init/android.hardware.boot-service.qti.rc`. fix9 was built that way and Android
  hung in vold (`boot-service.qti` aborts on `slotselect`); fix10 was built from fix8 and
  keeps both edits. The tool now tolerates an already-erased AVB footer, so fix8 can be
  passed as `--los`.
- `ReSuSFS_apply-uname.sh` exists but is **not** in the default
  `/data/adb/ReSuSFS/scripts_bootcompleted.txt`; add it (done) or the uname release reads the
  real `g16b58dc` after a reboot. Apply manually with
  `sh /data/adb/modules/ReSuSFS/ReSuSFS.sh --apply-uname /data/adb/ReSuSFS/uname.txt`;
  the script prints `set_uname '4.14.357-g050cbab6' …` on the current boot (ReSuSFS updates
  the release in `uname.txt`; the value is cosmetic).
- `ReSuSFS_apply-settings.sh` turns adb and developer options off and sets SELinux enforcing.
  It is commented out in `/data/adb/ReSuSFS/scripts_bootcompleted.txt` during bring-up.
- `ReSuSFS_apply-ksu-settings.sh` sets `kernel_umount=0`, `selinux_hide=1`. Even with
  kernel_umount off, `ksu_handle_umount()` calls `susfs_set_current_proc_umounted()` on its
  `skip_umount_task` path, so `TIF_PROC_UMOUNTED` is still set for zygote-spawned apps.
- `nsenter` into an app's mount namespace does **not** reproduce sus_path hiding: the flag is
  per-thread and only a real zygote child has it. Use an app-side detector instead.
- Verified spoofing: uname release is spoofed per boot (`4.14.357-g3edeb421` on the current
  boot; the real build is only in `dmesg`/`/proc/version` as
  `4.14.357-openela-perf-susfs-g3ab0ea5dad43`), `ro.debuggable=0`, `ro.secure=1`,
  `ro.boot.verifiedbootstate=green`, `ro.build.type=user`, `ro.build.tags=release-keys`,
  fingerprint `Xiaomi/laurel_sprout/laurel_sprout:11/RKQ1.200903.002/V12.0.26.0.RFQMIXM:user/release-keys`.
- Post-audit rebuild (2026-10-25, tip `3ab0ea5dad43`): 8 fixes — sus_mount mnt_id lifetime,
  sdcardfs `show_options2` options, fanotify_fdinfo prototype, smaps_rollup swap leak,
  `ksu_handle_sys_read` prototype, readdir EOF, cmdline-spoof consumer, fsnotify mark
  lifetime. The cmdline spoof is now effective: `/proc/cmdline` reads
  `/data/adb/ReSuSFS/cmdline_or_bootconfig.txt` (green/locked/enforcing).
- Detection: Ruru v1.1.1 (15) — Abnormal Environment, PM Command, PM Conventional/Sundry APIs,
  PM Intent Queries, Libc File Detection, Syscall File Detection, Xposed Modules: **all Not
  Found** (re-checked after the audit rebuild). The manager package is still enumerable
  (KernelSU hide-manager not configured).

## 15. Browser, captive portal, proxies, OSS camera (2026-10-25)

- **Browser:** LOS 24 does ship `org.lineageos.jelly` (launcher "Browser"), but **Cromite
  v153.0.8010.37** (`org.cromite.cromite`, arm64 APK sha256 `9db12af1…`) was installed as the
  daily browser (Chromium + adblock, GitHub releases).
- **Captive portal → Xiaomi CN** (persists in `Settings.Global`, works on LOS 24/Android 17):
  `captive_portal_mode=1`, `captive_portal_http_url`/`https_url`/`fallback_url`/
  `other_fallback_urls` = `http://(s)connect.rom.miui.com/generate_204`. Verified in logcat:
  `PROBE_HTTP/HTTPS … ret=204`, `isSuccessful()=true`, network `IS_VALIDATED`, Settings label
  "Connected" (`Server: MiFE/3.5.10`). Module options: `muink/Magisk-Captive-Manager` v2.1.4
  (2025-08, GPL-3, KernelSU/APatch compatible) is maintained; `Magisk-Captive-Control` (2020)
  and `tsukimio/captive-control` (2022) are stale. A module is only needed if you want a
  toggle/auto-reapply.
- **Proxy pitfall:** importing the Clash profile over `adb reverse` set
  `settings put global http_proxy 127.0.0.1:36000`. Deleting `http_proxy` does **not** clear
  `global_http_proxy_host/port`; NetworkMonitor then fails every probe with
  `Failed to connect to /127.0.0.1:36000` and Wi-Fi shows "No internet access" even with a
  working CN endpoint. Delete `global_http_proxy_{host,port,exclusion_list}` +
  `global_proxy_pac_url` and reboot (a Wi-Fi toggle alone kept the stale `ProxyInfo`).
- **OSS camera for SM6125** (IMX586 48 MP, S5K4H7 8 MP UW, OV02A10 2 MP depth, S5KGD1 32 MP;
  Camera2 `supportedHardwareLevel=3`): **PhotonCamera** (`bjzhou/PhotonCamera`, Apache-2.0,
  v1.28.5 2026-10-19, Qualcomm-optimized depth) is the active GCam-like choice and is installed
  (`com.hinnka.mycamera`, APK sha256 `918ea398…`, camera/audio granted; Pro/Photo/Video,
  EV/Tv/ISO/AF/AWB and LUT controls verified). **Open Camera** (GPLv3) is the manual/RAW/HDR
  alternative; LOS **Aperture** is preinstalled. GCam ports (BSG 9.6/9.7, BigKaka, Shamim)
  still exist but are niche in 2026.
- GCam port actually installed: **LMC 9.6 Release 1 Fix2 Xiaomi** (celsoazevedo
  `dev-hasli/f/dl22`), package `com.xiaomi.module.evaluation` (`versionName=LMC9.6v1`),
  APK sha256 `d11394928ffe8a1198de9c6898e6d7e30cdb7c1ac4e9eb6f089242f07fad3d82`.
  It opens Camera 0/1 and streams; UI has Night Sight/Portrait/Photo/Video and 1x/2x zoom.
  Launch with `am start -n com.xiaomi.module.evaluation/com.android.camera.CameraLauncher`
  — `monkey` injects random swipes that dismiss the camera (`EXIT_SELF`).
  Alternative: BSG `MGC_9.7.047_V34` (`dev-bsg/f/dl405`, `_MGC.apk` first). There is no
  maintained Mi A3/CC9e XML for GCam 9.x (old Mi A3 configs are GCam 7.x); LMC reads
  `/LMC9.6/` and defaults are fine for the IMX586 main / S5KGD1 front; aux lenses depend on
  the HAL and settings. Full port research/archive: `notes/gcam.md`.

## 16. Clash VPN routing — bypassable VPN bug (2026-10-25)

Symptom: app TCP/curl timed out while Clash's own rule-provider pulls worked, so it looked
like a dead node. It was **routing, not the proxy**: ClashMetaForAndroid defaults
`allow_bypass=true` (`ServiceStore.kt` → `TunService.kt` calls
`VpnService.Builder.allowBypass()`), so the VPN is **bypassable** and netd installs its UID
capture rule at `RULE_PRIORITY_BYPASSABLE_VPN = 24000` — *behind* the physical network's
`RULE_PRIORITY_IMPLICIT_NETWORK = 22998` (`fwmark 0x64/0x1ffff … lookup wlan0`). netd's
FwmarkServer stamps every app socket at `connect()` with `MARK=0xc0064` (netId 100 |
`PERMISSION_SYSTEM`), so app packets left wlan0 addressed to mihomo's **fake-IP** (`28.0.0.x`)
and hung. DNS used different rules and still reached tun0, which made it look like a proxy
fault.

Evidence: `tcpdump -i any` showed `<lan-ip>:x > 28.0.0.6:443 [S]` on wlan0 and
nothing on tun0; `iptables -t mangle -I OUTPUT … -j LOG` printed `MARK=0xc0064`;
`ip route get 28.0.0.6 mark 0xc0064` → `table wlan0`; a temporary
`ip rule add priority 5000 uidrange 2000-2000 lookup tun0` made curl return `200` and Clash log
the node chain (`🌐国外流量[…]`).

Fix (persists in app-private prefs):

```bash
adb shell 'am start -a com.github.metacubex.clash.meta.action.STOP_CLASH'
adb shell "su -c 'am force-stop com.github.metacubex.clash.meta'"
# edit /data/data/com.github.metacubex.clash.meta/shared_prefs/service.xml
#   <boolean name="allow_bypass" value="false" />
# owner 10179, mode 0660, then restorecon
adb shell 'am start -a com.github.metacubex.clash.meta.action.START_CLASH'
```

After the change `VpnTransportInfo{… bypassable=false}` and the capture rule is
`RULE_PRIORITY_SECURE_VPN = 13000`, ahead of wlan0's 22998. Verified 15:53 CST:
`generate_204` → 204, `example.com` → 200, Cromite renders, GMS proxied, 16 rule-providers
refreshed; selection persisted (`🌐国外流量 → 美国CHI落地01`, egress `64.20.4.37`).
Clash stop/start was verified; a **full reboot was not** (phone unplugged right after).
LAN bypass remains (expected, `bypassPrivateNetwork`); toggling "allow bypass" in the app UI
would rewrite the pref. Revert: set the key back to `true` (or remove it) with the service
stopped.

`START_CLASH`/`STOP_CLASH`/`TOGGLE_CLASH` are **activities** (`am start -a …`), not broadcasts.
Diagnostic that separates proxy from routing: use Clash's own HTTP proxy endpoint with
`curl -x http://IP:PORT` (port from `dumpsys connectivity`); `204` means the node chain is fine.
`/data/adb/ksu/bin/busybox` exists but is root-only — run it via `su -c` (a non-root probe
reports "inaccessible or not found").

**Community status:** this is a known footgun, not a novel bug. CMFA v2.11.36 ships
`allowBypass` with `defaultValue = true` (`ServiceStore.kt`) and the UI labels the toggle
"Allow Bypass — Allows all apps to bypass this VPN connection" / "允许应用绕过";
`TunService.kt` then calls `VpnService.Builder.allowBypass()`. Reports: CMFA discussion #466
(FCM/login broken until the bypass toggle was disabled), OpenClash #2884 (fake-IP + bypassed
clients cannot connect), and the ClashFest project changed its default to *disable*
allow-bypass in v0.3.2. The netd rule-priority numbers (13000/22998/24000) are Android
internals and are not usually quoted in those threads, but the symptom and the fix match.
Links: <https://github.com/MetaCubeX/ClashMetaForAndroid/discussions/466>,
<https://github.com/vernesong/OpenClash/issues/2884>,
<https://github.com/Nemu-x/ClashFest/commit/4397db4127acca187e6735cc05a2b70bce118c60>,
<https://github.com/MetaCubeX/ClashMetaForAndroid/blob/v2.11.36/service/src/main/java/com/github/kr328/clash/service/store/ServiceStore.kt>.

## 17. SELinux enforcing + perf kernel (2026-10-25)

Boot image is now repacked **without** `--permissive` and with
`--cmdline-extra "androidboot.selinux=enforcing"`; base LOS cmdline has no selinux token, so
enforcing is the default. Cold-boot verification: `boot_completed` in ~42 s, `getenforce` =
**Enforcing**, zero `avc: denied` at that build's boot (the later 35252 boot shows only
vendor-init denials: `laurus_logdump.sh` exec and sysfs wakeup setattr), `su` → `u:r:ksu:s0`, `ksud module list`,
`resetprop`, `ksu_susfs` and ReSuSFS status all work. LOS Trust (LineageParts) reports
**SELinux: Enforcing**; open it with
`adb shell am start -a org.lineageos.lineageparts.TRUST_INTERFACE` (activity
`org.lineageos.lineageparts/.trust.TrustPreferences`). Wi-Fi + Xiaomi CN probe 204; Clash
tun0 up, 204. Ruru was used earlier (all 8 checks Not Found); the old v1.1.1 APK is now
blocked by Play Protect on Android 17, so uname/props/cmdline spoof was spot-checked manually.

Perf flavor: `./build-laurus.sh susfs-perf build` (+ `vendor/laurus-susfs-perf.config`).
DEBUG_INFO, SCHED_DEBUG and SCHEDSTATS are off; image_size **51.93 MiB**; release
`4.14.357-openela-perf-susfs-g16b58dc8d946`. Boot
`boot-susfs-main-perf-enforcing.img` sha256 `41e1d8f5…1d1bb2`, vendor
`vendor-laurus-fix10.img` sha256 `2d64bf3d…0039de` (modules rebuilt/signed per build).
Permissive test boot `boot-susfs-main-perf-adb-permissive.img` sha256 `21994d7b…bbb6a`.

**Do not disable FTRACE for “performance”.** `CONFIG_BPF_EVENTS` depends on it; without the
GPU-mem BPF maps, `system_server` aborts in `libmeminfo`
(`BpfMapRO<unsigned long,unsigned long>::abortOnMismatch`, stack via
`ReadProcessGpuUsageKb`/`Debug.getGpuTotalUsageKb`) every ~10 s, so boot never completes.
That was the first perf attempt; it was rolled back with `boot-susfs-permissive-rollback.img`
(`404237b8…`) + `vendor-laurus-fix6.img` (`309e60d3…`), then rebuilt with FTRACE=y.
`FRAME_POINTER` is forced by arm64 4.14; `DEBUG_LIST` is selected by
`BUG_ON_DATA_CORRUPTION` (kept, hardening); `INIT_ON_ALLOC_DEFAULT_ON` is kept.
