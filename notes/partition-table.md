# CC9e (laurus) partition table

Parsed from the 2026-10-25 full dump, not from a live `sgdisk` run:

- `/mnt/hdd/laurus/full-backup-2026-10-25/gpt/sd{a..f}_head.bin` — the first 1 MiB of
  each UFS LUN. The GPT header is at **byte 4096** (LBA 1), not 512: the UFS logical
  block size is 4096. The partition-entry array is at LBA 2 (byte 8192), 128-byte
  entries, 32 entries per LUN except `sde` (64).
- `/mnt/hdd/laurus/full-backup-2026-10-25/metadata/by-name.txt` — the on-device
  `/dev/block/by-name` mapping. The `#` column below is the 1-based GPT entry, so
  `sde11` is GPT entry 10 and `boot`.
- LUN sizes (from `metadata/block_sizes.txt`, in 512-byte sectors): `sda` 123.4 GB,
  `sdb` 8 MB, `sdc` 8 MB, `sdd` 128 MB, `sde` 4 GB, `sdf` 128 MB.

The table covers all **84** by-name partitions. `userdata` is included but is not in
the raw-image backup (it was dumped as tarballs; see `BACKUP_REPORT.md`).

| LUN | # | partition | by-name node | first LBA | last LBA | size | GPT attrs |
|---|---:|---|---|---:|---:|---:|---|
| sda | 1 | `ssd` | `/dev/block/sda1` | 6 | 7 | 0.01 MiB | `0x0` |
| sda | 2 | `persist` | `/dev/block/sda2` | 8 | 8199 | 32.00 MiB | `0x0` |
| sda | 3 | `misc` | `/dev/block/sda3` | 8200 | 8455 | 1.00 MiB | `0x0` |
| sda | 4 | `keystore` | `/dev/block/sda4` | 8456 | 8583 | 0.50 MiB | `0x0` |
| sda | 5 | `frp` | `/dev/block/sda5` | 8584 | 8711 | 0.50 MiB | `0x0` |
| sda | 6 | `oem` | `/dev/block/sda6` | 8712 | 25095 | 64.00 MiB | `0x0` |
| sda | 7 | `oem_misc1` | `/dev/block/sda7` | 25096 | 25351 | 1.00 MiB | `0x0` |
| sda | 8 | `minidump` | `/dev/block/sda8` | 25352 | 58119 | 128.00 MiB | `0x0` |
| sda | 9 | `cust` | `/dev/block/sda9` | 58120 | 271111 | 832.00 MiB | `0x1000000000000000` |
| sda | 10 | `recovery` | `/dev/block/sda10` | 271112 | 287495 | 64.00 MiB | `0x0` |
| sda | 11 | `cache` | `/dev/block/sda11` | 287496 | 418567 | 512.00 MiB | `0x0` |
| sda | 12 | `system` | `/dev/block/sda12` | 418568 | 1729287 | 5.00 GiB | `0x0` |
| sda | 13 | `metadata` | `/dev/block/sda13` | 1729288 | 1733383 | 16.00 MiB | `0x0` |
| sda | 14 | `userdata` | `/dev/block/sda14` | 1733384 | 30119902 | 108.29 GiB | `0x0` |
| sdb | 1 | `xbl` | `/dev/block/sdb1` | 6 | 901 | 3.50 MiB | `0x1000000000000000` |
| sdb | 2 | `xbl_config` | `/dev/block/sdb2` | 902 | 2014 | 4.35 MiB | `0x0` |
| sdc | 1 | `xblbak` | `/dev/block/sdc1` | 6 | 901 | 3.50 MiB | `0x1000000000000000` |
| sdc | 2 | `xbl_configbak` | `/dev/block/sdc2` | 902 | 2014 | 4.35 MiB | `0x0` |
| sdd | 1 | `ALIGN_TO_128K_1` | `/dev/block/sdd1` | 6 | 31 | 0.10 MiB | `0x1000000000000000` |
| sdd | 2 | `cdt` | `/dev/block/sdd2` | 32 | 63 | 0.12 MiB | `0x1000000000000000` |
| sdd | 3 | `ddr` | `/dev/block/sdd3` | 64 | 32734 | 127.62 MiB | `0x1000000000000000` |
| sde | 1 | `rpm` | `/dev/block/sde1` | 6 | 133 | 0.50 MiB | `0x1000000000000000` |
| sde | 2 | `tz` | `/dev/block/sde2` | 134 | 1157 | 4.00 MiB | `0x1000000000000000` |
| sde | 3 | `hyp` | `/dev/block/sde3` | 1158 | 1285 | 0.50 MiB | `0x0` |
| sde | 4 | `modem` | `/dev/block/sde4` | 1286 | 52485 | 200.00 MiB | `0x1000000000000000` |
| sde | 5 | `bluetooth` | `/dev/block/sde5` | 52486 | 52741 | 1.00 MiB | `0x1000000000000000` |
| sde | 6 | `mdtpsecapp` | `/dev/block/sde6` | 52742 | 53765 | 4.00 MiB | `0x1000000000000000` |
| sde | 7 | `mdtp` | `/dev/block/sde7` | 53766 | 61957 | 32.00 MiB | `0x1000000000000000` |
| sde | 8 | `abl` | `/dev/block/sde8` | 61958 | 62213 | 1.00 MiB | `0x1000000000000000` |
| sde | 9 | `dsp` | `/dev/block/sde9` | 62214 | 70405 | 32.00 MiB | `0x1000000000000000` |
| sde | 10 | `keymaster` | `/dev/block/sde10` | 70406 | 70533 | 0.50 MiB | `0x1000000000000000` |
| sde | 11 | `boot` | `/dev/block/sde11` | 70534 | 86917 | 64.00 MiB | `0x0` |
| sde | 12 | `cmnlib` | `/dev/block/sde12` | 86918 | 87045 | 0.50 MiB | `0x1000000000000000` |
| sde | 13 | `cmnlib64` | `/dev/block/sde13` | 87046 | 87173 | 0.50 MiB | `0x1000000000000000` |
| sde | 14 | `devcfg` | `/dev/block/sde14` | 87174 | 87205 | 0.12 MiB | `0x0` |
| sde | 15 | `qupfw` | `/dev/block/sde15` | 87206 | 87221 | 0.06 MiB | `0x0` |
| sde | 16 | `vendor` | `/dev/block/sde16` | 87222 | 349365 | 1.00 GiB | `0x0` |
| sde | 17 | `vbmeta` | `/dev/block/sde17` | 349366 | 349381 | 0.06 MiB | `0x1000000000000000` |
| sde | 18 | `dtbo` | `/dev/block/sde18` | 349382 | 355525 | 24.00 MiB | `0x0` |
| sde | 19 | `imagefv` | `/dev/block/sde19` | 355526 | 356037 | 2.00 MiB | `0x1` |
| sde | 20 | `uefisecapp` | `/dev/block/sde20` | 356038 | 356549 | 2.00 MiB | `0x0` |
| sde | 21 | `rpmbak` | `/dev/block/sde21` | 356550 | 356677 | 0.50 MiB | `0x0` |
| sde | 22 | `tzbak` | `/dev/block/sde22` | 356678 | 357701 | 4.00 MiB | `0x0` |
| sde | 23 | `hypbak` | `/dev/block/sde23` | 357702 | 357829 | 0.50 MiB | `0x0` |
| sde | 24 | `modembak` | `/dev/block/sde24` | 357830 | 409029 | 200.00 MiB | `0x1000000000000000` |
| sde | 25 | `bluetoothbak` | `/dev/block/sde25` | 409030 | 409285 | 1.00 MiB | `0x1000000000000000` |
| sde | 26 | `mdtpsecappbak` | `/dev/block/sde26` | 409286 | 410309 | 4.00 MiB | `0x1000000000000000` |
| sde | 27 | `mdtpbak` | `/dev/block/sde27` | 410310 | 418501 | 32.00 MiB | `0x1000000000000000` |
| sde | 28 | `ablbak` | `/dev/block/sde28` | 418502 | 418757 | 1.00 MiB | `0x1000000000000000` |
| sde | 29 | `dspbak` | `/dev/block/sde29` | 418758 | 426949 | 32.00 MiB | `0x1000000000000000` |
| sde | 30 | `keymasterbak` | `/dev/block/sde30` | 426950 | 427077 | 0.50 MiB | `0x1000000000000000` |
| sde | 31 | `bootbak` | `/dev/block/sde31` | 427078 | 443461 | 64.00 MiB | `0x0` |
| sde | 32 | `cmnlibbak` | `/dev/block/sde32` | 443462 | 443589 | 0.50 MiB | `0x1000000000000000` |
| sde | 33 | `cmnlib64bak` | `/dev/block/sde33` | 443590 | 443717 | 0.50 MiB | `0x1000000000000000` |
| sde | 34 | `devcfgbak` | `/dev/block/sde34` | 443718 | 443749 | 0.12 MiB | `0x0` |
| sde | 35 | `qupfwbak` | `/dev/block/sde35` | 443750 | 443765 | 0.06 MiB | `0x0` |
| sde | 36 | `vbmetabak` | `/dev/block/sde36` | 443766 | 443781 | 0.06 MiB | `0x1000000000000000` |
| sde | 37 | `dtbobak` | `/dev/block/sde37` | 443782 | 449925 | 24.00 MiB | `0x0` |
| sde | 38 | `imagefvbak` | `/dev/block/sde38` | 449926 | 450437 | 2.00 MiB | `0x1` |
| sde | 39 | `uefisecappbak` | `/dev/block/sde39` | 450438 | 450949 | 2.00 MiB | `0x0` |
| sde | 40 | `devinfo` | `/dev/block/sde40` | 450950 | 450950 | 0.00 MiB | `0x1000000000000000` |
| sde | 41 | `dip` | `/dev/block/sde41` | 450951 | 451206 | 1.00 MiB | `0x1000000000000000` |
| sde | 42 | `apdp` | `/dev/block/sde42` | 451207 | 451270 | 0.25 MiB | `0x0` |
| sde | 43 | `spunvm` | `/dev/block/sde43` | 451271 | 453318 | 8.00 MiB | `0x0` |
| sde | 44 | `splash` | `/dev/block/sde44` | 453319 | 461674 | 32.64 MiB | `0x0` |
| sde | 45 | `limits` | `/dev/block/sde45` | 461675 | 461675 | 0.00 MiB | `0x1000000000000000` |
| sde | 46 | `toolsfv` | `/dev/block/sde46` | 461676 | 461931 | 1.00 MiB | `0x1000000000000000` |
| sde | 47 | `logfs` | `/dev/block/sde47` | 461932 | 463979 | 8.00 MiB | `0x0` |
| sde | 48 | `cateloader` | `/dev/block/sde48` | 463980 | 464491 | 2.00 MiB | `0x0` |
| sde | 49 | `rawdump` | `/dev/block/sde49` | 464492 | 497259 | 128.00 MiB | `0x0` |
| sde | 50 | `logdump` | `/dev/block/sde50` | 497260 | 513643 | 64.00 MiB | `0x0` |
| sde | 51 | `bk03` | `/dev/block/sde51` | 513644 | 513707 | 0.25 MiB | `0x0` |
| sde | 52 | `storsec` | `/dev/block/sde52` | 513708 | 513739 | 0.12 MiB | `0x1000000000000000` |
| sde | 53 | `multiimgoem` | `/dev/block/sde53` | 513740 | 513747 | 0.03 MiB | `0x1000000000000000` |
| sde | 54 | `multiimgqti` | `/dev/block/sde54` | 513748 | 513755 | 0.03 MiB | `0x1000000000000000` |
| sde | 55 | `uefivarstore` | `/dev/block/sde55` | 513756 | 513883 | 0.50 MiB | `0x1000000000000000` |
| sde | 56 | `secdata` | `/dev/block/sde56` | 513884 | 513890 | 0.03 MiB | `0x1000000000000000` |
| sde | 57 | `catefv` | `/dev/block/sde57` | 513891 | 514018 | 0.50 MiB | `0x1000000000000000` |
| sde | 58 | `catecontentfv` | `/dev/block/sde58` | 514019 | 1048542 | 2.04 GiB | `0x1000000000000000` |
| sdf | 1 | `ALIGN_TO_128K_2` | `/dev/block/sdf1` | 6 | 31 | 0.10 MiB | `0x1000000000000000` |
| sdf | 2 | `modemst1` | `/dev/block/sdf2` | 32 | 543 | 2.00 MiB | `0x0` |
| sdf | 3 | `modemst2` | `/dev/block/sdf3` | 544 | 1055 | 2.00 MiB | `0x0` |
| sdf | 4 | `fsg` | `/dev/block/sdf4` | 1056 | 3615 | 10.00 MiB | `0x1000000000000000` |
| sdf | 5 | `fsc` | `/dev/block/sdf5` | 3616 | 32734 | 113.75 MiB | `0x0` |

## Notes

- **Sizes are in 4 KiB LBA units.** A 64 MiB partition is 16,384 LBAs; `boot` is
  `70534..86917` = 16,384 LBAs. The last LBA is inclusive.
- The `0x1000000000000000` attribute is **bit 60**, inside the AB-attribute range
  (`AB_FLAG_OFFSET = 54` in the device's `gpt-utils.h`); bit 60 is
  `AB_PARTITION_ATTR_BOOT_SUCCESSFUL`. It is not a generic "read-only" flag. `imagefv`
  uses `0x1` (a partition-type-specific bit). Treat the raw value as authoritative.
- `sde` has 64 GPT slots but only 58 are used; `sda`/`sdb`/`sdc`/`sdd`/`sdf` use 32.
- `userdata` is 108.29 GiB and is not a raw image in the backup (it is tarballs).
- **Do not restore `sda_head.bin`/`sda_tail.bin` wholesale.** They are 1 MiB windows
  around the GPT, not the full LUN, and contain live bytes. Restore only the GPT ranges
  (`notes/cc9e-notes.md` §5.1): primary LBA 0..5 and backup entries at
  `last_lba - 32`; never write the whole window.
- The `by-name` mapping is the device's; a partition's node can move if the GPT is
  rewritten. Re-read `metadata/by-name.txt` after any GPT change.
