# ABL `BootLinux` — where the 52 MiB kernel window comes from

This is the static confirmation of the CC9e kernel-size limit. No device flash was needed; the
ABL from the stock laurus A9 fastboot ROM was unpacked and decompiled.

Binary: `/mnt/hdd/laurus/downloads/rom-a9/laurus_images_V10.2.13.0.PFMCNXM_20190830.0000.00_9.0_cn/images/abl.elf`
(ELF32 ARM, 151,552 B, LOAD at `0x9fa00000`).

## 1. `abl.elf` is an ELF wrapper around a UEFI firmware volume

At file offset `0x3000` (vaddr `0x9fa00000`) the payload starts with a UEFI FV:

```
9fa00020: 00 20 02 00 00 00 00 00 5f 46 56 48 ...   FvLength 0x22000, "_FVH"
9fa00048: 93 fd 21 9e 72 9c 15 4c ...                FFS file GUID
9fa00060: 88 fb 01 02 98 58 4e ee 14 39 59 42 ...   section size/type + guided-section GUID
```

- `EFI_FIRMWARE_VOLUME_HEADER` at `0x9fa00000`, header length `0x48`.
- One FFS file at `0x9fa00048`; its data starts with an `EFI_SECTION_GUID_DEFINED` at
  `0x9fa00060`.
- The guided-section GUID is `EE4E5898-3914-4259-9D6E-DC7BD79403CF` (LZMA compression).
- `DataOffset = 0x18`; the LZMA stream starts at `0x9fa00078`, not `0x9fa0007c`: the offset is
  relative to the section header, not the GUID. Decompressing the stream gives **434,376 bytes**.

The decompressed data contains a PE32+ EFI application:

```
000000b8: 4d 5a ...                 MZ
00000f10: 50 45 00 00 ...           PE, Machine 0xAA64 (ARM64), 3 sections
```

Carving from `0xb8` to the end of the last section (`0x6a000` bytes, `SizeOfImage`) gives
`abl_pe.bin`; IDA loads it as an ARM64 EFI application with 573 functions. The strings identify
it as the `LinuxLoader` application:

```
LinuxLoader
/home/work/laurus-p-stable-build/.../QcomModulePkg/Application/LinuxLoader/LinuxLoader.c
ANDROID!
Invalid image Sizes
KernelSize: %u, PageSize=%u
Not Enough space left to load kernel image
Kernel size is over the limit
Compute Kernel Load Address: 0x%x
Compute Kernel Size Actual: 0x%x
Compute Ramdisk Load Address: 0x%x
```

## 2. `sub_F460` is `UpdateBootParams` / `BootLinux`

IDA's `sub_F460` (0xF460) contains the boot image parser (`sub_118F8`, `ANDROID!`) and the
address/size logic. The relevant decompiled lines:

```c
v9  = 54525952;                 // 0x3400000 = 52 MiB
v10 = 52428800;                 // 0x3200000 = 50 MiB
*(v3 - 112) = v43 | 0x80000;    // KernelLoadAddr  = BaseMemory | 0x80000
*(v3 - 96)  = v43 | 0x3400000;  // KernelEndAddr   = BaseMemory | 0x3400000
*(v3 - 88)  = v43 | 0x3200000;  // 32-bit fallback = BaseMemory | 0x3200000
```

`v43` is the "Memory Base Address" printed by the code; for this boot memory map it is
`0x40000000`. The constants are the fallback PCDs, and they match the upstream source.

## 3. The upstream logic

Source: `QcomModulePkg/Library/BootLib/BootLinux.c` and `BootLinux.h` (Qualcomm EDK2 tree).
The exact flow:

```c
/* QueryBootParams reads UEFI variables KernelBaseAddr and KernelSize */
if (QueryBootParams (&KernelBaseAddr, &KernelSizeReserved)) {
    KernelLoadAddr = KernelBaseAddr;
    KernelLoadAddr += (32bit ? KERNEL_32BIT_LOAD_OFFSET : KERNEL_64BIT_LOAD_OFFSET);
    KernelEndAddr = KernelBaseAddr + KernelSizeReserved;
} else {
    /* fallback PCDs */
    KernelLoadAddr = BaseMemory | PcdGet32 (KernelLoadAddress);
    KernelEndAddr  = BaseMemory + PcdGet32 (RamdiskEndAddress);
}

RamdiskLoadAddr = KernelEndAddr
                - round_up (RamdiskSize + VendorRamdiskSize, PageSize)
                - PageSize;
DeviceTreeLoadAddr = RamdiskLoadAddr - (DT_SIZE_2MB + PageSize);

if (DeviceTreeLoadAddr <= KernelLoadAddr)
    error ("Not Enough space left to load kernel image");

if (KernelLoadAddr + KernelSizeActual > KernelEndAddr)
    error ("Kernel size is over the limit");
```

`BootLinux.h` defines:

```c
#define KERNEL_32BIT_LOAD_OFFSET  0x8000
#define KERNEL_64BIT_LOAD_OFFSET  0x80000
#define DT_SIZE_2MB               (2 * 1024 * 1024)
```

The ABL's own strings and the decompiled checks match these exactly:
`Not Enough space left to load kernel image`, `Kernel size is over the limit`,
`Ramdisk Size Actual`, `Compute Ramdisk Load Address`.

## 4. What the numbers mean

- **64-bit fallback:** kernel load `BaseMemory | 0x80000` = `0x40080000`; kernel end
  `BaseMemory + 0x3400000` = `0x43400000`; the fallback window is
  `0x43400000 - 0x40080000 = 0x3380000 = 51.5 MiB`.
- **32-bit fallback:** `0x8000` / `0x3200000` = 50 MiB end.
- **UEFI-variable path:** `KernelEndAddr = KernelBaseAddr + KernelSize`. The observed known-good
  51.957 MiB image ends at `0x43475000`, so `KernelEndAddr` must be above that; the natural
  value is `0x43480000` (52 MiB from the load address, 52.5 MiB from `0x40000000`).
  The XBL memory map reserves `0x40000000 + 0x05700000` (87 MiB) for the "Kernel" region, so
  the ramdisk/DTB fit above the kernel window.
- **Effective kernel window: 52 MiB**, from `0x40080000` to `0x43480000`. The known-good
  images end at `0x4346c000`/`0x4346f000`/`0x43475000` (44–80 KiB headroom); the debug
  61.84 MiB image ends at `0x43e57000` (9.84 MiB over) and is rejected.

The exact runtime `KernelSize` UEFI variable is not in the persistent `uefivarstore` dump
(the variables are set at runtime by XBL), so the 52 MiB end is pinned by the ABL fallback,
the source, and the known-good/known-bad boundary. It is not an arbitrary gate: the ABL
contains `0x3400000` (52 MiB) as the 64-bit fallback, and the variable path is consistent with
the same 52 MiB window.

## 4a. Field note — `image_size` vs the ABL's `KernelSizeActual`

The ABL checks `KernelLoadAddr + KernelSizeActual > KernelEndAddr`, where
`KernelSizeActual` is the **decompressed kernel blob** rounded up to a page, not the arm64
Image header `image_size` (which includes BSS). Measured:

| build | `image_size` | decompressed | ABL headroom in 52 MiB |
|---|---:|---:|---:|
| LOS prebuilt | 51.92188 | 48.333 MiB | 3.666 MiB |
| BakaSU rc3 | 51.93359 | 48.341 MiB | 3.658 MiB |
| SukiSU | 51.95703 | 48.355 MiB | 3.644 MiB |
| debug | 61.83984 | 55.990 MiB | **−3.990 MiB** |

So the “44–80 KiB headroom” quoted in `notes/bringup-2026-10-25.md` is only the
`image_size` margin; the ABL itself has ~3.6 MiB for the known-good kernels, and the debug is
~4.0 MiB over the ABL check (not 9.84 MiB). `image_size` includes BSS, which the bootloader
does not copy. The 51.96 gate was a conservative proxy; keep it (or ≤48 MiB) anyway, because
BSS/memory layout and future config changes can move both numbers.

Build check: compute both the arm64 `image_size` and the decompressed `zlib` length; fail at
50 MiB (48 MiB for margin) for either. `tools/repack_los_boot.py` prints `image_size`; the
decompressed length is easy to add.

## 5. Practical rule

- 51.96 MiB is the largest measured booting `image_size`; 61.84 MiB is the measured failing one.
- The effective limit is 52 MiB; keep new builds **≤48 MiB** for headroom.
- The 32-bit path is 50 MiB, but this device boots a 64-bit kernel; the 64-bit path applies.
- Do not generalize to other devices: the offsets/PCDs come from this ABL and XBL memory map.

## Reproduce

```sh
# 1. carve the FV from the ELF LOAD segment at 0x9fa00000
dd if=abl.elf of=/tmp/abl_fv.bin bs=1 skip=$((0x3000)) count=$((0x22000))
# 2. parse the FFS/guided section (see above), extract the LZMA stream at 0x78 in the FV
#    and decompress to /tmp/abl_decomp.bin
# 3. carve the PE at 0xb8, open in IDA
```

The LZMA stream is `FORMAT_ALONE` with props `0x5d` and dict size `0x01000000`; Python's
`lzma.decompress(data, format=lzma.FORMAT_ALONE)` yields the 434,376 B PE container.

## References

- `BootLinux.c` / `BootLinux.h`, `SHIFTPHONES/android_bootable_bootloader_edk2` (`sos-3.x`).
- `avb_vbmeta_image.h` and `notes/avb-vbmeta.md` for the AVB side of boot.
- `notes/bringup-2026-10-25.md` for the failed-boot evidence.
