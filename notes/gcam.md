# GCam on laurus — port research and installed setup

Date: 2026-10-25. Device: Xiaomi Mi CC9e `laurus` (SM6125), LineageOS 24 / Android 17,
A3 vendor HAL, Camera2 `supportedHardwareLevel = 3` (LEVEL_3) on all camera devices.

## TL;DR

**Installed: LMC 9.6 Release 1 Fix2 — Xiaomi variant** (closed-source, free).
Package `com.xiaomi.module.evaluation` (`versionName=LMC9.6v1`), launcher
`com.android.camera.CameraLauncher`. It opens Camera 0/1, streams, and shows the full GCam UI
(Night Sight, Portrait, Photo, Video, 1×/2× zoom).

- APK: `/mnt/hdd/laurus/downloads/LMC9.6_Release_1_Fix2_Xiaomi.apk`
  (293,534,556 B, sha256 `d11394928ffe8a1198de9c6898e6d7e30cdb7c1ac4e9eb6f089242f07fad3d82`)
- Source: <https://www.celsoazevedo.com/files/android/google-camera/dev-hasli/f/dl22/>
- Alternative (not downloaded): **BSG MGC 9.7.047_V34**
  <https://www.celsoazevedo.com/files/android/google-camera/dev-bsg/f/dl405/>
  (`_MGC.apk` first, `_snap.apk` if it won't open).

## Camera hardware

| role | sensor | notes |
|---|---|---|
| rear main | Sony **IMX586** 48 MP | quad-bayer; GCam uses 12 MP binned by default |
| rear ultrawide | Samsung **S5K4H7** 8 MP | aux lens — only if the port/HAL exposes it |
| rear depth | OmniVision **OV02A10** 2 MP | aux/depth; not a normal photo lens |
| front | Samsung **S5KGD1** 32 MP | works as a normal front camera |

All five camera device IDs report Camera2 **LEVEL_3**, so GCam's normal requirements are met.
GCam ports are not sensor-specific: support comes from Camera2 + the vendor HAL. IMX586 and
S5KGD1 are common and work; the two aux sensors depend on whether the port enumerates them
and on the HAL's stream configuration.

## Why LMC 9.6 Xiaomi

- Current (LMC 9.6, 2026) and shipped as an explicit **Xiaomi** build, unlike the generic
  BSG/AGC APKs.
- GCam 9.x line is what current Android versions expect; the old Mi A3 community configs are
  GCam **7.x** era and do not apply to 9.x.
- Closed source is fine for this use; the port is free. Open-source alternatives are listed
  below.

## Install / launch

```sh
adb install -r LMC9.6_Release_1_Fix2_Xiaomi.apk
adb shell am start -n com.xiaomi.module.evaluation/com.android.camera.CameraLauncher
```

Grant `CAMERA`/`RECORD_AUDIO`/`READ_MEDIA_IMAGES`/`READ_MEDIA_VIDEO` (the first launch asks
for camera):

```sh
pkg=com.xiaomi.module.evaluation
for p in CAMERA RECORD_AUDIO READ_MEDIA_IMAGES READ_MEDIA_VIDEO; do
  adb shell pm grant $pkg android.permission.$p
done
```

Quirks:

- **Never launch it with `monkey`.** Monkey's random events include swipes; they dismissed the
  camera (`onGestureAnimationStart … edge-swipe` then `EXIT_SELF`), which looks like a crash.
  Use `am start -n …` only.
- The Xiaomi build masquerades as `com.xiaomi.module.evaluation`; that is the package to
  uninstall (`adb uninstall com.xiaomi.module.evaluation`), not a Google package name.
- Harmless log noise: `PhenotypeFlagCommitter: … GoogleCertificatesRslt: not allowed` and
  `Unable to initialize lighting estimation model` (portrait relighting) do not stop capture.

## Configs

- GCam 9.x for this device has **no maintained device config**. The Mi A3 XMLs that circulate
  on XDA are for GCam 7.x (Parrot/Urnyx/HyperCam) and are not usable with LMC 9.6.
- LMC reads configs from `/LMC9.6/` on internal storage; load via the config interface
  (long-press the dark area near the shutter). Default profile (`Profile 1`,
  `Active config: OFF`) already works for the main/front cameras.
- BSG's config UI uses the same "double-tap the dark area near the shutter" idiom; its config
  pages are at <https://www.celsoazevedo.com/files/android/google-camera/configs/c/bsg-97/>.
- Aux lenses: enable/expose them in the port's settings if present. Expect the S5K4H7
  ultrawide to be the realistic second lens; the OV02A10 is a depth sensor.

## Alternatives (2026)

| port | status / notes |
|---|---|
| **LMC 9.6 (Hasli)** | installed; Xiaomi build; current; config folder `/LMC9.6/` |
| **BSG MGC 9.7.047_V34** | current (Oct 2026); APK variants `_MGC`, `_snap`, etc.; start with `_MGC` |
| **AGC (BigKaka) 9.x** | active; supports many devices; configs community-made |
| **Shamim SGCAM 9.x** | active; another common fallback |
| **PhotonCamera** | open source (Apache-2.0, bjzhou fork), installed; GCam-like computational photography |
| **Open Camera** | GPLv3, manual/RAW/HDR, Camera2; not installed |
| **Aperture** | LOS default, preinstalled |

Port hub: <https://www.celsoazevedo.com/files/android/google-camera/>. GCam development in
2026 is niche but alive (BSG's Telegram ~43k subscribers; celsoazevedo still publishes
current builds).

## APK archive

All session APKs live in `/mnt/hdd/laurus/downloads/` on the workstation HDD (the repo is
text-only). Copy to the Mac's `/tmp` during a session was temporary only.

| file | size (B) | sha256 |
|---|---|---|
| `LMC9.6_Release_1_Fix2_Xiaomi.apk` | 293,534,556 | `d11394928ffe8a1198de9c6898e6d7e30cdb7c1ac4e9eb6f089242f07fad3d82` |
| `PhotonCamera-1.28.5-default.apk` | 61,813,725 | `918ea398f3606924d2316ba33c185f1980700100cbe6e1377ad867df473b6f4f` |
| `arm64_ChromePublic.apk` (Cromite 153) | 323,809,949 | `9db12af1af021f42b4371e76d0e9fe476a7085bbbbc76bc410a538d028bf6071` |
| `cmfa-2.11.36-meta-arm64-v8a-release.apk` (Clash Meta) | 47,623,688 | `7da3083c16af676f9a3e478e3f42098b91803cbd7cb637bff4117d4d50360f95` |
| `Ruru.1.1.1.15.apk` | 2,740,592 | `8a2856cd13353c18402f1ba31bb1a7320d8aaa4aedd7391f1bd7d75ef889b056` |
| `ReSuSFS-v26.10.23.zip` (upstream) | 267,182 | `e09e71645170f715c3ce98ce74aa0f17fa1faba3e9533862010e905260e6dd34` |
| `ReSuSFS-v26.10.23-offline.zip` (patched) | 263,733 | `181d1568dde5f30f0ae69123dd938b9c59e01067bba3ccce083431812276fc98` |
| `ksu_susfs_arm64` (upstream CLI) | 24,392 | `21303cef99048d83bf689d33c3b474a872697c9c4583c45049c2b72a14c66de5` |

**Not downloaded:** BSG MGC 9.7 (link only). `Magisk-v30.7.apk` predates this session.

## Test notes

- LMC opens `Camera 0` and `Camera 1` and the HAL logs `Start camera streaming for
  com.xiaomi.module.evaluation`; the UI exposes Night Sight, Portrait, Photo, Video, 1×/2×
  zoom and settings.
- The first screenshot had a black viewfinder because the phone was lying face-down on the
  desk; PhotonCamera was black at the same moment. Not a port failure.
- 48 MP output is not expected from a normal GCam config on this sensor; GCam shoots 12 MP
  binned. Treat 48 MP as a separate experiment.

## References

- LMC 9.6 release: <https://www.celsoazevedo.com/files/android/google-camera/dev-hasli/f/dl22/>
- BSG 9.7 release: <https://www.celsoazevedo.com/files/android/google-camera/dev-bsg/f/dl405/>
- BSG 9.6/9.7 configs: <https://www.celsoazevedo.com/files/android/google-camera/configs/c/bsg-96/>,
  <https://www.celsoazevedo.com/files/android/google-camera/configs/c/bsg-97/>
- GCam hub: <https://www.celsoazevedo.com/files/android/google-camera/>
- PhotonCamera: <https://github.com/bjzhou/PhotonCamera>
- Open Camera: <https://opencamera.org.uk/>
- Historical Mi A3 GCam threads (GCam 7.x, for reference only):
  <https://xdaforums.com/t/best-gcam-mi-a3.3968317/>,
  <https://xdaforums.com/t/mi-a3-gcam-config.4035479/>
