# vendor_compare — where each file came from

| file | source | sha256 (first 16) |
|---|---|---|
| `laurus_mixer_paths_qrd.xml` | CC9e vendor V10.2.13.0.PFMCNXM (A9), `/vendor/etc/` (`backups/2026-10-25/vendor.img`) | `2fcb8418f6876cf7` |
| `laurus_audio_platform_info_qrd.xml` | same | `e89ce8260ac754d5` |
| `laurus_audio_platform_info_intcodec.xml` | same; **the platform file the CC9e HAL actually loads** (speaker acdb_id 10011 matches logcat) | `2a6b4abc51d5ef49` |
| `a3_a9_mixer_paths_qrd.xml` | stock Mi A3 V10.3.4.0.PFQEUXM (A9) vendor, GitHub `catrielmuller/xiaomi_laurel_sprout_dump` | `2fcb8418f6876cf7` |
| `a3_a9_audio_platform_info_intcodec.xml` | same dump | `ac691c372d4f260a` |
| `a3_a11_mixer_paths_qrd.xml` | stock Mi A3 V12.0.26.0.RFQMIXM (A11) vendor, GitHub `anirudhkosgi/xiaomi_laurel_sprout_dump` — the firmware base the LOS 24 OTA names | `2e76dba34c0fd1cd` |
| `a3_a11_audio_platform_info_intcodec.xml` | same dump | `af74a18f6c1070c2` |
| `los24_mixer_paths_qrd.xml` | LOS 24 `vendor.img` from `lineage-24.0-20261020-nightly-laurel_sprout-signed.zip`; identical to `device/xiaomi/laurel_sprout/audio/mixer_paths_qrd.xml` (source file in the LOS device tree, not a proprietary blob) | `50e5098e4ca19c57` |
| `los24_audio_platform_info_intcodec.xml` | LOS 24 vendor (= A3 A11 file with `input_mic_max_count` 4 → 2) | `306bdd86cad62944` |

Findings:
- A3 A9 and CC9e A9 `mixer_paths_qrd.xml` are **byte-identical**.
- LOS's files are the stock A3 A11 ones, imported in one commit (`000debe` "laurel_sprout: Import audio
  configs", 2025-02-05) with two changes already applied: mic gains raised in `mixer_paths_qrd.xml`
  (`TX_DEC0..7 Volume` 84 → 102, `ADC1..3 Volume` 12 → 14) and `input_mic_max_count` 4 → 2 in
  `audio_platform_info_intcodec.xml`.
- A3 A9 vs CC9e A9 intcodec: the CC9e adds `SND_DEVICE_*_GAME_*` devices (MIUI game mode), otherwise the same.
