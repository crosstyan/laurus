#!/usr/bin/env bash
# Follow the phone through boot attempts and save every log source as soon as it is
# reachable. Start it BEFORE `fastboot boot` / reboot; stop with Ctrl-C.
#
#   tools/capture_boot_logs.sh [OUTDIR]        (default: logs/losboot-<timestamp>)
#
# Per state change it creates OUTDIR/<NN>-<state>/:
#   fastboot  -> getvar.txt (fastboot getvar all)
#   device    -> props.txt, cmdline.txt, pstore/ (records of the PREVIOUS boot),
#                logcat-last.txt (pmsg of the previous boot), then live logcat.txt
#                (-b all) and dmesg.txt until the device drops; boot_completed is
#                logged in capture.log when it flips
#   recovery  -> (TWRP) pstore/, last_kmsg, dmesg.txt, recovery.log, props.txt
#   unauthorized/offline -> noted in capture.log (use a boot-*-adb image, or authorize)
# Root: `adb root` when the build allows it (the -adb boot images do), else `su -c`.
set -u
OUT=${1:-logs/losboot-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$OUT"
LOG=$OUT/capture.log
n=0
state=none
pids=()

log() { printf '[%s] %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }

stop_streams() {
  for p in ${pids[@]+"${pids[@]}"}; do kill "$p" 2>/dev/null; done
  wait ${pids[@]+"${pids[@]}"} 2>/dev/null
  pids=()
}
trap 'stop_streams; log "stopped"; exit 0' INT TERM

current_state() {
  local s
  s=$(adb get-state 2>&1 | tr -d '\r')
  case $s in
    device|recovery|sideload|bootloader) echo "$s"; return ;;
    *unauthorized*) echo unauthorized; return ;;
    *offline*) echo offline; return ;;
  esac
  fastboot devices 2>/dev/null | grep -q . && { echo fastboot; return; }
  echo none
}

# run a command as root on the device: adbd root if available, else su
rsh() {
  if [[ $(adb shell id -u 2>/dev/null | tr -d '\r') == 0 ]]; then adb shell "$@"
  else adb shell "su -c '$*'"; fi
}

# pmsg-ramoops is binary: copy on the device and adb pull (streaming through su can
# rewrite LF -> CRLF)
grab_pstore() { # dir
  local t=/data/local/tmp/pstore.capture
  mkdir -p "$1/pstore"
  rsh "ls -la /sys/fs/pstore/" > "$1/pstore/ls.txt" 2>&1
  rsh "rm -rf $t; mkdir -p $t; cp /sys/fs/pstore/* $t/ 2>/dev/null; chmod -R a+rX $t"
  adb pull "$t/." "$1/pstore/" >/dev/null 2>&1
  rsh "rm -rf $t"
  log "  pstore: $(ls "$1/pstore" | grep -v '^ls.txt$' | tr '\n' ' ')"
}

on_device() { # dir
  local d=$1
  adb root >/dev/null 2>&1 && sleep 2 && adb wait-for-any-device >/dev/null 2>&1
  log "  root: $( [[ $(adb shell id -u 2>/dev/null | tr -d '\r') == 0 ]] && echo adbd-root || echo su/none)"
  adb shell getprop > "$d/props.txt" 2>&1
  rsh "cat /proc/cmdline" > "$d/cmdline.txt" 2>&1
  log "  $(grep -E '\[ro.build.(display.id|fingerprint)\]' "$d/props.txt" | head -1)"
  grab_pstore "$d"
  adb logcat -L -b all -v threadtime -d > "$d/logcat-last.txt" 2>&1
  adb logcat -b all -v threadtime > "$d/logcat.txt" 2>&1 & pids+=($!)
  if [[ $(adb shell id -u 2>/dev/null | tr -d '\r') == 0 ]]; then
    adb shell dmesg -w > "$d/dmesg.txt" 2>&1 & pids+=($!)
  else
    adb shell "su -c 'dmesg -w'" > "$d/dmesg.txt" 2>&1 & pids+=($!)
  fi
  log "  streaming logcat + dmesg"
}

on_recovery() { # dir
  local d=$1
  grab_pstore "$d"
  adb shell "cat /proc/last_kmsg" > "$d/last_kmsg" 2>&1
  adb shell dmesg > "$d/dmesg.txt" 2>&1
  adb pull /tmp/recovery.log "$d/recovery.log" >/dev/null 2>&1
  adb shell getprop > "$d/props.txt" 2>&1
  log "  recovery logs saved"
}

log "capturing into $OUT"
booted=0
while :; do
  s=$(current_state)
  if [[ $s != "$state" ]]; then
    stop_streams
    log "state: $state -> $s"
    state=$s; booted=0
    if [[ $s != none ]]; then
      n=$((n + 1)); dir=$(printf '%s/%02d-%s' "$OUT" "$n" "$s"); mkdir -p "$dir"
      case $s in
        fastboot) fastboot getvar all > "$dir/getvar.txt" 2>&1; log "  getvar saved" ;;
        device) on_device "$dir" ;;
        recovery) on_recovery "$dir" ;;
        unauthorized) log "  adb unauthorized: authorize on screen, or boot a *-adb image" ;;
      esac
    fi
  fi
  if [[ $state == device && $booted == 0 ]]; then
    if [[ $(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r') == 1 ]]; then
      booted=1; log "  sys.boot_completed=1"
    fi
  fi
  sleep 1
done
