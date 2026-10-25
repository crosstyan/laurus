# CC9e (laurus) — hardware inventory from the running device

Captured 2026-10-25 from `<redacted-device-serial>` (CC9e running A3 system).
Sources: `logs/dmesg_*.log`, `logs/getprop_*.txt`, `logs/logcat_*.log`, the CC9e vendor image
(`backups/2026-10-25/vendor.img`, read with `debugfs`). Re-validated 2026-10-24; corrections marked *(corrected)*.

## Cameras (actually probed at boot)

| role | kernel probe name | sensor | module vendor | fuse id prop |
|---|---|---|---|---|
| rear main | `laurus_imx586_sunny probe succeeded` | Sony **IMX586** 48 MP | Sunny | `camera.sensor.rearMain.fuseID = <redacted-fuse-id>` |
| rear ultrawide | `laurus_s5k4h7_sunny probe succeeded` | Samsung **S5K4H7** 8 MP (120° FoV) | Sunny | `camera.sensor.rearAux.fuseID = <redacted-fuse-id>` (rearAux = the S5K4H7) |
| rear depth | `laurus_ov02a10_sunny probe succeeded` | OmniVision **OV02A10** 2 MP | Sunny | — (no EEPROM in `camera_config.xml`) |
| front | `laurus_s5kgd1_sunny probe succeeded` | Samsung **S5KGD1** 32 MP | Sunny | `camera.sensor.frontMain.fuseID = <redacted-fuse-id>` |

`persist.camera.sensor.name = laurus_imx586_sunny` (main sensor detected). This unit is all-Sunny.

*(corrected)* The vendor also ships configs for the alternate batches: `laurus_imx582_qtech` (+ `_india`,
`_factory`) and `laurus_gc2375_qtech` (+ `_india`) — **QTech only** — and `laurus_ov13855_sunny`, which is
**dormant** (its `camera_config.xml` block is commented out, no EEPROM lib). "OFILM" exists only for the
S5KGD1. These are **not CC9e-specific**: the A3 vendor carries the same `laurus_*` set.

## Touchscreen

- Driver: **FocalTech FTS_TS**, input device `fts_ts` at `4a88000.i2c/i2c-1/1-0038`, chip id 0x5452 = **FT3518**.
- Goodix `goodix_ts_probe` runs first and **fails** (`i2c test FAILED`, error -1000 on 0x5d) — so the
  **touch controller** is FocalTech, not Goodix *(corrected: the panel itself is the Samsung S6E8FC0 AMOLED)*.

## Fingerprint

- `persist.vendor.sys.fp.vendor = goodix_fod`, `ro.hardware.fp.fod=true` → **Goodix under-display** fingerprint
  (`gf_spi: goodix fingerprint fod init status = 0x0`; `/vendor/lib64/hw/fingerprint.goodix_fod.so`).
- (`fpc1020_init OK` in dmesg is just the FPC driver being present; no other FPC activity.)

## Sensors (from `/vendor/etc/sensors/config/`)

| config | part | function |
|---|---|---|
| `bmi160_0.json`, `nicobar_qrd_bmi160_0.json` | `bmi160` SSC driver config; the schematic symbol is **BMI120** | accelerometer + gyroscope |
| `ak991x_dri_0.json`, `nicobar_qrd_ak991x_0.json` | AKM **AK09918C** (schematic page 30) *(corrected: confirmed by schematic, not inference)* | magnetometer / compass |
| `stk3x3x_0.json`, `nicobar_qrd_stk3x3x_0.json` | Sensortek **STK3x3x** (configured; light/prox events seen in logcat, chip id not logged) | ambient light + proximity |
| `sx932x_0.json`, `nicobar_qrd_gpio129_sx932x_0.json`, `nicobar_qrd_gpio131_sx932x_0.json` | Semtech **SX9325** in the schematic (page 39); population unverified | SAR / grip |
| `pah_8011_0_platform.ppg_enable_ex_{1,2}.json` | PixArt **PAH8011** | PPG config for soc 300/301 MTP/Surf only — never matches this phone |

HAL `sensors.ssc.so` (`/vendor/etc/sensors/hals.conf`). *(corrected)* The earlier "46 sensors" count has no
local source (42 JSON files in the config dir; no `dumpsys sensorservice` capture saved).

## Power

- Battery: `S88512_mtp_Sunwoda_4V4_4030mAh` → **Sunwoda 4030 mAh** (QG: `battery_profile=…`, healthd `fc=4030000`).
- Charger: PMI632 v2.0 (`smblib`), QG fuel gauge.

## Boot logging status

- pstore/ramoops **registered**: `pstore: Registered ramoops as persistent store backend`,
  `ramoops: attached 0x100000@0x61600000, ecc: 4/0`, `console [pstore-1] enabled`
  (DT: console-size 0x40000, record-size 0x80000).
- *(corrected)* The contents of `/sys/fs/pstore/` and `/proc/last_kmsg` were **not captured** (an `ls` of a
  procfs file shows 0 bytes regardless). After a hang/panic the previous console should appear as
  `/sys/fs/pstore/console-ramoops-0` (warm reboot only).
- Boot logs saved (a boot that completed at 10-24 21:28, captured 10-25 02:18):
  - `logs/dmesg_<ts>.log` (~0.9 MB, kernel, includes boot)
  - `logs/logcat_<ts>.log` (~1.4 MB: main/system/radio/events/crash buffers)
  - `logs/getprop_<ts>.txt`

## A3 vs CC9e — research verdict (re-validated 2026-10-24)

**Same components.** A3 = M1906F9SH (global) / M1906F9SI (India); CC9e = M1906F9SC (China, confirmed on
this unit via `ro.product.cert`). Same S88512 board, same dimensions (153.48 × 71.85 × 8.475 mm),
same 6.088" 720x1560 AMOLED (web sources). The A3 is the global / Android One sibling of the CC9e.

DTS: MiCode `laurus-p-oss` (Android P) contains both `arch/arm64/boot/dts/qcom/laurus-qrd.dtsi` and
`laurel_sprout-qrd.dtsi` (they differ); Q/R use separate branches. *(corrected)* The LOS tree used here has
no laurus DTS — its A3 DT is `arch/arm64/boot/dts/xiaomi/laurel_sprout/laurel_sprout-trinket-*.dtsi`.

The A3 vendor blob set is named `laurus_*` (722 of 1122 lines in the LOS `proprietary-files.txt`;
the A3 kernel matches `laurus_imx586_sunny` etc.). The names are shared; the `libmmcamera_laurus_*.so`
binaries differ by build (A9 / A10 / A3 A11).

### Cameras — same sensors, same Xiaomi part numbers (A3 side web-verified)

| position | sensor (primary → alternate) | module makers | Xiaomi mac_no |
|---|---|---|---|
| rear main 48 MP | Sony **IMX586** → **IMX582** (QTech only; 4K30 vs 4K60) | IMX586: Sunny, QTech | 414480450092 |
| rear ultrawide 8 MP | Samsung **S5K4H7** | Sunny, QTech | 414800450092 |
| rear depth 2 MP | OmniVision **OV02A10** → **GC2375** | Sunny (OV), QTech (GC) | 414200450092 |
| front 32 MP | Samsung **S5KGD1** | Sunny, OFILM | 413320450092 |
| dormant front | OV13855 (config commented out; present only in the CC9e A9 vendor) | Sunny | — |

The mac_no numbers are confirmed for the A3 at a UK reseller (Headlane); the CC9e side and the
"CN repair-parts API" claim are unverified. One number covers all sensor/maker variants.
`camera_config.xml`: CC9e A9 vs A3 A11 blobs differ by one commented-out OV13855 block; CC9e A10
(V12.5.5) is **byte-identical** to the A3. IMX582 as second source: Wang Teng, 2019-07-03 (CC9e).
Suffixes `_india`/`_global`/`_factory` encode tuning; `factory` chromatix is CC9e-only.

### Sensors / touch / fingerprint — same parts

| function | part |
|---|---|
| accel + gyro | `bmi160` driver config (schematic: BMI120) |
| magnetometer | AKM **AK09918C** (schematic) |
| light + proximity | Sensortek **STK3x3x** (configured) |
| SAR | Semtech **SX9325** in schematic; population unknown |
| fingerprint | **Goodix FOD** (`soc/goodix_fp`, `gf_spi.c`, `fingerprint.goodix_fod.so`) *(corrected: `goodix_firmware.bin` is the Goodix GTx8 touch firmware, not the fingerprint's)* |
| touch | dual-source **FocalTech FT3518** or **Goodix GT9883** (+ a Synaptics TCM DT node); this unit = FT3518 |

Sensor JSONs are byte-identical across CC9e A9, CC9e A10 and A3. The CC9e DT adds touch tuning
(`fts,touch-tolerance-*`, `fts,edgefilter-*`), `xiaomi_touch` and `simtray`; see `cc9e-notes.md` §3.

## Schematic source (S88512AA1, A3 + CC9e)

- https://secyukle.com/dosya/uploads/schematics/Xiaomi%2BMi%2BA3%2B%28laurel%29%2BMi%2BCC9e%2B%28laurus%29%2BSchematic.rar
  (2,328,092 bytes, last-modified 2022-12-03, HTTP 200)
- https://androidfilehost.com/?fid=8889791610682869368
- listing: https://www.dzkj16888.com/index.php?c=read&desc=0&id=23017&page=1
- Local: `misc/schematic/` — `schematic_S88512AA1.PDF` (title `S88512AA1_1_21_20190515_1605`)
  sha256 5de393f588164bc0c37a1d81588dc459828856bbcabb28c5de40052af3fe46e0;
  `board_top_bottom_artfilm.pdf` (board rev `88512_1_20`)
  sha256 9638d66006c1360494c7f5d5cac8a54d59097533fdeddec8cd0d80f130c00359.
