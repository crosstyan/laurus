#!/usr/bin/env bash
# Build the LOS sm6125 kernel for laurus.
#   ./build-laurus.sh ref   [config|build]   LOS-identical config  -> out-ref
#   ./build-laurus.sh debug [config|build]   + laurus-debug.config -> out-laurus-debug
#   ./build-laurus.sh sukisu [config|build]  + laurus-sukisu.config (worktree sm6125-sukisu) -> out-sukisu
# "build" (default) also runs "config". Outputs: arch/arm64/boot/Image.gz, *.ko in
# <out>/modules/, vmlinux (unstripped, for addr2line/gdb).
set -euo pipefail
cd "$(dirname "$0")"
SRC=$PWD/android_kernel_xiaomi_sm6125
CLANG=/mnt/hdd/laurus/build/prebuilts/clang/kernel/linux-x86/clang-r416183b/bin
# toolchain-bin/clang wraps clang with --cuda-path=/nonexistent: otherwise
# "Found CUDA installation" from `clang -v` lands in compile.h and breaks init/version.c
export PATH=/mnt/hdd/laurus/build/toolchain-bin:$CLANG:$PATH

flavor=${1:?ref|debug}; step=${2:-build}
case $flavor in
  ref)    OUT=$PWD/out-ref;           FRAGS=() ;;
  debug)  OUT=$PWD/out-laurus-debug;  FRAGS=(vendor/laurus-debug.config) ;;
  # SukiSU-Ultra lives in a separate worktree (drivers/kernelsu -> ../SukiSU-Ultra/kernel)
  sukisu) SRC=$PWD/sm6125-sukisu; OUT=$PWD/out-sukisu; FRAGS=(vendor/laurus-sukisu.config) ;;
  # BakaSU (manual hooks) lives in its own worktree (drivers/kernelsu vendored from ../BakaSU/kernel)
  bakasu) SRC=$PWD/sm6125-bakasu; OUT=$PWD/out-bakasu; FRAGS=(vendor/laurus-bakasu.config) ;;
  *) echo "unknown flavor $flavor" >&2; exit 1 ;;
esac
# same order as TARGET_KERNEL_CONFIG in device/xiaomi/{sm6125-common,laurel_sprout}
BASE=vendor/trinket-perf_defconfig
FRAGS=(vendor/xiaomi-trinket.config vendor/laurel_sprout.config "${FRAGS[@]}")

MAKE=(make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 LLVM_IAS=1 CC=clang
      CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu-
      -j"$(nproc)")

"${MAKE[@]}" "$BASE" >/dev/null
( cd "$SRC" && ARCH=arm64 scripts/kconfig/merge_config.sh -m -O "$OUT" "$OUT/.config" \
    "${FRAGS[@]/#/arch/arm64/configs/}" >/dev/null )
"${MAKE[@]}" olddefconfig >/dev/null

# every option a fragment asks for must survive olddefconfig
for f in "${FRAGS[@]}"; do
  grep -E '^(CONFIG_[A-Z0-9_]+=|# CONFIG_[A-Z0-9_]+ is not set)' "$SRC/arch/arm64/configs/$f" |
  while read -r want; do
    grep -qxF "$want" "$OUT/.config" || echo "WARN [$f] not applied: $want"
  done
done
[[ $step == config ]] && { echo "config ready: $OUT/.config"; exit 0; }

if ! "${MAKE[@]}" Image.gz modules > "$OUT/build.log" 2>&1; then
  grep -E 'error:|Error [0-9]' "$OUT/build.log" | head -20 >&2
  echo "BUILD FAILED, see $OUT/build.log" >&2; exit 1
fi
rm -rf "$OUT/modules"
"${MAKE[@]}" INSTALL_MOD_PATH="$OUT/modules-install" INSTALL_MOD_STRIP=1 modules_install >/dev/null
mkdir -p "$OUT/modules" && find "$OUT/modules-install" -name '*.ko' -exec cp {} "$OUT/modules/" \;
echo "kernel: $OUT/arch/arm64/boot/Image.gz ($(cat "$OUT/include/config/kernel.release"))"
echo "modules: $(ls "$OUT/modules")"
