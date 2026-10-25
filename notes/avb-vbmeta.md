# AVB, vbmeta, dm-verity, and the Magisk/fstab question

This is the long version of the three gates a cross-flash has to open: **AVB** (bootloader
verification), **dm-verity** (runtime block verification), and **force-encrypt/FBE**
(`/data`). It also explains the `misc` BCB workaround and what changed in Magisk.

Official sources used below:

- [Android Verified Boot](https://source.android.com/docs/security/features/verifiedboot/avb)
- [Boot flow](https://source.android.com/docs/security/features/verifiedboot/boot-flow)
- [Implement dm-verity](https://source.android.com/docs/security/features/verifiedboot/dm-verity)
- [AVB README](https://android.googlesource.com/platform/external/avb/+/android17-release/README.md)
- [`avb_vbmeta_image.h`](https://android.googlesource.com/platform/external/avb/+/android17-release/libavb/avb_vbmeta_image.h)
  and the descriptor headers in the same directory.
- [AOSP `bootloader_message_core.h`](https://android.googlesource.com/platform/bootable/recovery/+/android17-release/bootloader_message/include/bootloader_message/bootloader_message_core.h)
- Magisk: [issue #6141](https://github.com/topjohnwu/Magisk/issues/6141),
  [commit 810d27a](https://github.com/topjohnwu/Magisk/commit/810d27a618908621a7eca32f9adccab2611746ee)

## 1. What AVB validates

The Android docs say AVB is the Verified Boot 2.0 reference implementation for Project
Treble; `libavb` is the boot-time library, and the bootloader must provide the root of
trust, platform I/O, and rollback-index storage. The AVB README describes the trust chain:

> The central data structure used in AVB is the VBMeta struct. This data structure contains
> a number of descriptors (and other metadata) and all of this data is cryptographically
> signed. Descriptors are used for image hashes, image hashtree metadata, and so-called
> chained partitions.

So the bootloader does **not** hash every byte of `system` at boot. It:

1. Loads the top-level `vbmeta` partition.
2. Verifies the vbmeta signature with the OEM public key embedded in the bootloader
   (or a custom root of trust).
3. If verification is enabled, walks the descriptors:
   - **hash descriptor** — an image (boot, dtbo, recovery) is hashed at boot and compared
     with the digest;
   - **hashtree descriptor** — the bootloader trusts the root hash/salt/tree offset; the
     kernel's dm-verity target verifies blocks lazily at runtime;
   - **chain partition descriptor** — verification is delegated to another vbmeta
     (in this dump: `system` has its own signed vbmeta in its AVB footer);
   - **property/kernel-cmdline descriptors** — key/value metadata and boot args.
4. Checks the rollback index against the stored value.
5. Reports the result as `androidboot.verifiedbootstate` and `androidboot.veritymode`.

The boot-flow page defines the states:

> The bootloader sets the `androidboot.verifiedbootstate` option to one of the following
> values: `green` if the device is `LOCKED` and user-settable root of trust isn't used;
> `yellow` if the device is `LOCKED` and user-settable root of trust is used; `orange` if
> the device is `UNLOCKED`. The `androidboot.veritymode` option is set to `eio` or `restart`
> depending on which state the bootloader is in with respect to handling dm-verity errors.

The three red states are: `eio` (dm-verity corruption), no valid OS, and a locked-device
verification failure. On an **unlocked** device the bootloader shows the orange warning and
continues; it does not turn a modified system into a brick. That is why every cross-flash
starts with `fastboot flashing unlock`.

The device's backup `cmdline.txt` (before the SUSFS cmdline spoof) shows the real state:
`androidboot.verifiedbootstate=orange`; the current `/proc/cmdline` is spoofed to
`green`/`locked` by ReSuSFS. `ro.boot.vbmeta.device_state=unlocked` is the real property.

## 2. The vbmeta binary layout

The header is fixed at **256 bytes**; the image is three blocks:

```
+-----------------------------------------+  offset 0
| Header data - fixed 256 bytes           |
+-----------------------------------------+  offset 256
| Authentication data - variable size     |  hash + signature (64-byte aligned)
+-----------------------------------------+  offset 256 + auth_size
| Auxiliary data - variable size          |  descriptors + public key + metadata
+-----------------------------------------+  offset 256 + auth_size + aux_size
```

All fields are **network byte order** (big-endian). The `AvbVBMetaImageHeader` comments give
the exact offsets:

| off | field | size | meaning |
|---:|---|---:|---|
| 0 | `magic` | 4 | `"AVB0"` |
| 4 | `required_libavb_version_major` | 4 | minimum libavb major |
| 8 | `required_libavb_version_minor` | 4 | minimum libavb minor |
| 12 | `authentication_data_block_size` | 8 | signature block size |
| 20 | `auxiliary_data_block_size` | 8 | aux block size |
| 28 | `algorithm_type` | 4 | 0=none, 1=SHA256_RSA2048, 2=SHA256_RSA4096, 3=SHA256_RSA8192, 4=SHA512_RSA2048, 5=SHA512_RSA4096, 6=SHA512_RSA8192 |
| 32 | `hash_offset` | 8 | offset into auth block |
| 40 | `hash_size` | 8 | hash length |
| 48 | `signature_offset` | 8 | offset into auth block |
| 56 | `signature_size` | 8 | signature length |
| 64 | `public_key_offset` | 8 | offset into aux block |
| 72 | `public_key_size` | 8 | public key length |
| 80 | `public_key_metadata_offset` | 8 | offset into aux block |
| 88 | `public_key_metadata_size` | 8 | metadata length |
| 96 | `descriptors_offset` | 8 | offset into aux block |
| 104 | `descriptors_size` | 8 | descriptors length |
| 112 | `rollback_index` | 8 | image rollback index |
| 120 | `flags` | 4 | see below |
| 124 | `rollback_index_location` | 4 | stored-index slot (top-level only) |
| 128 | `release_string` | 48 | e.g. `avbtool 1.1.0` |
| 176 | `reserved` | 80 | zero |

The flags field has exactly two defined bits; everything else in the header is a field, not
a bitmap. From `avb_vbmeta_image.h`:

> `AVB_VBMETA_IMAGE_FLAGS_HASHTREE_DISABLED`: If this flag is set, hashtree image
> verification will be disabled.
>
> `AVB_VBMETA_IMAGE_FLAGS_VERIFICATION_DISABLED`: If this flag is set, verification will be
> disabled and descriptors will not be parsed.

So:

| bit | mask | name | effect |
|---:|---:|---|---|
| 0 | `0x1` | `HASHTREE_DISABLED` | dm-verity hashtree descriptors are not enforced |
| 1 | `0x2` | `VERIFICATION_DISABLED` | descriptors are not parsed at all |
| 2..31 | — | reserved | must be zero |

`0x3` = both bits = "do not verify this vbmeta's descriptors, and do not set up dm-verity
from its hashtree descriptors". That is exactly what the CC9e's stock vbmeta has after the
flags byte was patched.

### Descriptors

Each descriptor starts with:

```c
typedef struct AvbDescriptor {
  uint64_t tag;
  uint64_t num_bytes_following;
} AvbDescriptor;
```

The tag values are:

| tag | descriptor | what it carries |
|---:|---|---|
| 0 | property | key/value (e.g. version info) |
| 1 | hashtree | dm-verity version, image size, tree offset/size, block sizes, FEC, hash algorithm, partition name, salt, root digest, flags |
| 2 | hash | image size, hash algorithm, partition name, salt, digest, flags |
| 3 | kernel cmdline | flags + command line |
| 4 | chain partition | rollback-index location, partition name, trusted public key, flags |

The descriptor structs are in `avb_hash_descriptor.h`, `avb_hashtree_descriptor.h`, and
`avb_chain_partition_descriptor.h`; all fields are big-endian, followed by the variable
name/salt/digest or name/public-key bytes. `flags` in a hash/hashtree descriptor is not the
vbmeta flags: it has its own `DO_NOT_USE_AB` bit, etc.

### The actual CC9e `vbmeta`

Parsed from `backups/2026-10-25/vbmeta.img` (the stock vbmeta with only the flags byte
patched):

```
magic AVB0, libavb 1.0
auth 320, aux 2048, algorithm 1 (SHA256_RSA2048)
hash 0/32, signature 32/256
public key 1472/520, metadata 1992/0
descriptors 0/1472
rollback_index 0, flags 3, rollback_index_location 0
release "avbtool 1.1.0"
file size 65536 (partition), used 2624
```

`avbtool info_image` lists:

| descriptor | partition | key data |
|---|---|---|
| chain | `system` | rollback location 2; trusted key SHA1 `b2a02f1e…` |
| hashtree | `vendor` | image 1,056,714,752 B; tree 8,327,168 B; FEC 8,421,376 B; SHA-1; salt `0337c9…`; root `7062adeb…` |
| hash | `dtbo` | 161,743 B; SHA-256 |
| hash | `boot` | 14,098,432 B; SHA-256 |
| hash | `recovery` | 22,183,936 B; SHA-256 |

The `system` image has its own signed vbmeta in its AVB footer (flags 0, hashtree descriptor
for the 5,283,917,824 B original image; the partition is 5,368,709,120 B; tree 41,611,264 B;
FEC 42,106,880 B). The top-level chain descriptor delegates to it. The `vendor` footer has an **unsigned** (`Algorithm: NONE`) vbmeta with the
same hashtree descriptor; the signed top-level descriptor is the trust anchor. `boot` and
`dtbo` have no AVB footer at all; their hashes live only in the top-level vbmeta.

Because the flags byte was changed after signing, the signature is invalid:

```
$ avbtool verify_image --image vbmeta.img
avbtool: Signature check failed for SHA256_RSA2048 vbmeta struct
```

That is acceptable **only because the bootloader is unlocked**. A locked bootloader would
reject the patched vbmeta and show the red "no valid OS" screen. On this device the
`vbmeta` flags 3 make the bootloader skip the descriptors; the `avbtool` output still lists
them because they are still in the image.

## 3. dm-verity is the second, separate gate

AVB signs the **root** of the dm-verity hash tree; dm-verity enforces the tree at runtime.
The Android docs:

> dm-verity lets you look at a block device... and determine if it matches its expected
> configuration. It does this using a cryptographic hash tree. For every block (typically
> 4k), there is a SHA256 hash. Because the hash values are stored in a tree of pages, only
> the top-level "root" hash must be trusted to verify the rest of the tree.

The flow is:

1. The hashtree descriptor in `vbmeta` (or in a chained partition's vbmeta) carries the
   root digest, salt, data/hash block size, tree offset/size and FEC offset/size.
2. The boot ramdisk's fstab has `verify` on the system/vendor line.
3. `fs_mgr`/`init` passes the descriptor to the kernel's dm-verity target.
4. Every read is hashed up the tree; a mismatch returns `EIO` (and the bootloader/OS may
   show the red `eio` state).

Disabling AVB with flags `0x3` does **not** automatically edit the fstab. If the fstab still
says `verify`, `fs_mgr` may still try to set up dm-verity; if the hashtree is disabled or
the image changed, that can fail. On this project both sides were patched:

- `tools/repack_los_boot.py` strips `slotselect` and `avb` from the boot ramdisk's
  `first_stage_ramdisk/system/etc/fstab.qcom` and `system/etc/recovery.fstab`.
- The vendor `/etc/fstab.qcom` was patched to remove `slotselect` and the A/B boot-control
  HAL; otherwise `vold` waits forever.
- The boot image's kernel and the vendor's modules are a per-build signed pair.

The vendor fstab's `userdata` line uses **FBE** (`fileencryption=aes-256-xts:…`,
`keydirectory=/metadata/vold/metadata_encryption`), not the old `forceencrypt`. FBE is
normal on Android 10+; do not remove `fileencryption` unless you deliberately want
unencrypted data. `forceencrypt`/`forcefdeorfbe` are the old "encrypt on first boot" flags;
if present and you do not want forced encryption, remove them and format data.

## 4. `misc` is the BCB, not a magic partition

`misc` holds the Android bootloader control block (`bootloader_message_core.h`):

```c
struct bootloader_message {
  char command[32];     // "boot-recovery", "boot-fastboot", ...
  char status[32];
  char recovery[768];   // recovery command line
  char stage[32];
  char reserved[1184];  // total 2048 bytes
};
```

The bootloader reads `command` on every boot. `boot-recovery` means "boot the recovery
partition"; `bootonce-bootloader` means "next boot to fastboot", etc. Xiaomi's stock
system/OTA can restore the stock recovery on the next normal boot; a stale BCB can also
send the phone to recovery. Flashing a known `misc` image clears/sets that state, and
booting straight into TWRP (Volume Up + Power) means the stock system never runs first.
The laurus stock `misc.img` is all zeros; the exact content of BeastROM's `misc.bin` was
not verified. Treat the step as a workaround, not a rule. A full laurus fastboot ROM also
writes `misc` (the image is zeros in the A9 ROM), which clears any pending command.

## 5. Magisk: what changed, and how to do it properly

Older Magisk (the 2019 guide used 19.4) patched the boot ramdisk's fstab **when it found
one**: it removed `verify` (dm-verity) and `forceencrypt` so that a modified system/data
could boot. That is what the guide's "you HAVE TO flash Magisk" refers to on its boot
image. On this CC9e's original boot the ramdisk has no fstab and the appended DTBs carry no
fstab/avb entries; there the vbmeta flags alone were the verity gate (`notes/cc9e-notes.md`
§2). So the correct model is "vbmeta flags + fstab if it exists"; Magisk was never a
universal gate.

Newer Magisk changed this. The 2SI rework (commit `810d27a`, "Use /data as tmpfs mount
point in 2SI setup", v24.3/24303) removed the fstab-patching step from `magiskinit`; the
Magisk issue #6141 describes the resulting boot loops on devices that still rely on the
old patch. `scripts/boot_patch.sh` still exposes `KEEPVERITY` and `KEEPFORCEENCRYPT`, and
`magiskboot cpio … "patch"` can still apply them, but **do not rely on Magisk to disable
AVB/dm-verity**. Do it explicitly.

### The explicit sequence

1. **Unlock the bootloader.** `fastboot flashing unlock` (data wipe; Xiaomi may require the
   168-hour wait). Do not relock.
2. **Disable AVB on the top-level vbmeta.** Use the laurus vbmeta, never the A3 one:
   ```sh
   fastboot --disable-verity --disable-verification flash vbmeta laurus-vbmeta.img
   ```
   This patches the flags to `0x3`. The signature becomes invalid; that is fine on an
   unlocked bootloader. Equivalent offline: `avbtool make_vbmeta_image --flags 3 …`, or
   patch the flags byte at offset 120 of an existing image and flash it. Verify:
   ```sh
   avbtool info_image --image vbmeta.img | grep -E 'Flags|Rollback'
   ```
3. **Patch the boot ramdisk fstab.** Remove `avb` and `verify` (and `slotselect` on an
   A-only phone). Remove `forceencrypt`/`forcefdeorfbe` only if you do not want forced
   encryption; keep `fileencryption` if you want FBE. Use `tools/repack_los_boot.py` (it
   already strips `slotselect`/`avb`) or `magiskboot`:
   ```sh
   magiskboot unpack boot.img
   # edit ramdisk.cpio: first_stage_ramdisk/system/etc/fstab.qcom, system/etc/recovery.fstab
   magiskboot repack boot.img new-boot.img
   ```
   The `magiskboot cpio … "patch"` form uses `KEEPVERITY`/`KEEPFORCEENCRYPT`; setting both
   to `true` leaves your edits alone. The project's repack tool is the reproducible path.
4. **Format `/data` and `/metadata`.** A cross-ROM cannot decrypt the old `/data`; format it
   (`fastboot erase userdata` is enough on this LOS build; it formats f2fs) and
   `fastboot format:ext4 metadata` (never bare erase). If you keep data, you need the old
   keymaster/FBE keys to match; that is the risky path.
5. **Install Magisk only for root**, after the boot image is already patched. Verify it did
   not undo the fstab/flags:
   ```sh
   avbtool info_image --image vbmeta.img | grep Flags
   adb shell 'dmesg | grep -i -E "verity|avb"'
   adb shell getprop ro.boot.veritymode
   ```
   If you use Magisk's boot patch, set `KEEPVERITY=true KEEPFORCEENCRYPT=true` so it does
   not touch your fstab edits, or inspect the patched ramdisk before flashing.

On this project, Magisk is not used at all: BakaSU/SUSFS is the root solution, and the boot
image is repacked with `repack_los_boot.py` (no Magisk). The same three gates apply.

## 6. `avbtool` cheat sheet

```sh
avbtool info_image       --image vbmeta.img          # header + descriptors
avbtool verify_image     --image vbmeta.img          # signature check (fails after flags patch)
avbtool calculate_vbmeta_digest --image vbmeta.img   # androidboot.vbmeta.digest
avbtool make_vbmeta_image --flags 3 --output vbmeta.img ...
avbtool add_hash_footer  --image boot.img --partition_name boot \
         --partition_size 67108864 --hash_algorithm sha256 --salt HEX
avbtool add_hashtree_footer --image system.img --partition_name system \
         --partition_size 5368709120 --hash_algorithm sha1 --salt HEX
avbtool erase_footer     --image vendor.img          # remove a stale footer
```

`--flags 3` is the offline equivalent of
`fastboot --disable-verity --disable-verification`. The flags are part of the signed header,
so changing them invalidates the signature; the bootloader must be unlocked (or the vbmeta
re-signed with a key it trusts, which a retail Xiaomi bootloader will not).

## 7. The one-line model

- **AVB** = "is the vbmeta signed, and do its descriptors match the images?"
- **dm-verity** = "does every block read from system/vendor hash to the tree rooted in the
  descriptor?"
- **force-encrypt/FBE** = "can this system mount `/data` with the keys it has?"
- **misc/BCB** = "which mode does the bootloader enter next?"
- **Magisk (old)** patched the fstab to skip the second and third; **Magisk (new)** does
  not, so patch them yourself.
