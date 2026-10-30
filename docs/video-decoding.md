# Hardware video decoding

This build uses Steam Frame's Qualcomm Iris decoder through V4L2. The
launcher enables `AcceleratedVideoDecoder` alongside `OpenXR`. The build
selects V4L2 exclusively, so it needs no VA-API driver or backend preference
flag. Chromium retains its software decoders for fallback.

## Build settings

`build/build.sh` writes these settings on every prepare run:

```gn
use_v4l2_codec = true
use_vaapi = false
use_av1_hw_decoder = true
use_v4l2_stateless_av1_decoder = false
```

The final setting is introduced by patch 0003. It defaults to the previous
stateless behavior when V4L2 and hardware AV1 are enabled, and this recipe
overrides it for Iris. It gates the stateless delegate, request controls,
logging, test tool and advertised stateless AV1 format. Stateful `AV01`
discovery and profile mapping remain enabled. The Linux sysroot lacks the
stateless AV1 API definitions; disabling all hardware AV1 would also remove
the stateful path needed by Iris.

Patch 0002 supplies `config.coded_size()` when configuring the compressed
input queue. Iris uses those dimensions to size its session buffers and
rejects allocation when Chromium supplies `0 x 0`.

## Driver requirements

On the tested SteamOS 0.5.6 installation, `/dev/video-dec0` points to
`/dev/video22`, driven by `iris_driver`. The `steamos` account can access it.
Chromium discovers numbered `/dev/video*` devices on Linux.

| Codec | Driver requirement | Validation |
|---|---|---|
| H.264 | Stock driver exposing `H264` | Chromium 156: 1080p60 playback and native WebXR passed |
| HEVC | Driver exposing `HEVC` and a supported profile | Playback not tested |
| VP9 | Driver exposing `VP90` and a supported profile | Playback not tested |
| AV1 | Driver exposing `AV01` and a usable decoded output format | Chromium 156 selects V4L2, but the tested backport stalls during output setup; see below |

The [experimental Iris AV1 backport](https://github.com/mmis1000/steamframe-iris-av1-poc)
adds AV1 to the tested kernel `6.18.0-g83913f38113c`. Its separate build and
temporary-load instructions describe the matching kernel requirement and
rollback. This browser installer installs only Chromium and its launcher.
Loading a different driver requires restarting Chromium to refresh codec
discovery.

The backport's direct V4L2 tests decoded 4K60 for 120 seconds (7,200 frames)
and 8K30 for 120 seconds (3,600 frames), with no missing frames, buffer
errors or sampled-pixel mismatches. These used looped 8-bit synthetic clips.
8K60 stalled at decoder startup. Browser rendering, WebXR texture upload,
10-bit/HDR and film grain need separate validation.

## Validation record

- October 26, 2026: Chromium 156.0.8071.0 with V4L2 enabled and patch 0002
  displayed 682 frames of H.264 1080p60 with zero reported drops. Media
  diagnostics identified `V4L2VideoDecoder` with platform decoding enabled.
  A YouTube stereo stream also used V4L2, and native WebXR produced both eye
  poses while playback advanced at about 60 fps in the measured sample.
- October 30, 2026: the headset was reachable with its stock driver and
  advertised H.264, HEVC and VP9. AV1 was absent, as expected after reboot.
- October 30, 2026: a complete ARM64 Chromium 156.0.8071.0 build with the
  AV1 changes was tested on the headset with the temporary Iris AV1 module.
  Hardware decoder selection succeeded, but playback stalled before the
  first frame. The measurements and output-format issue are recorded below.
- The recipe targets Chromium 157.0.8103.15. Full compilation and on-device
  playback of that exact release remain required.
- All three patches applied and passed their reverse checks against the
  pinned 157 sources. Launcher checks preserved the WebXR and decoding
  features, a URL containing spaces and the software-decoding override.

Run `python3 build/check-patches.py` to repeat the source check. An optional
version argument checks another release. The Check recipe workflow runs
this check and shell syntax validation on pushes and pull requests.

## Chromium AV1 runtime test: October 30, 2026

The test used SteamOS 0.5.6, kernel `6.18.0-g83913f38113c`, Chromium
156.0.8071.0 and the temporary Iris AV1 backport. The browser was staged
separately from the installed browser. Media was stored on the headset to
exclude network throughput. The pinned Chromium 157 build was still
running when these results were recorded.

Hardware attempts reported `V4L2VideoDecoder` and
`kIsPlatformVideoDecoder=true` in Chromium's media diagnostics:

| AV1 input | Hardware browser result |
|---|---|
| Synthetic 3840×2160, 60 fps | Zero displayed frames; startup timed out after 20 seconds |
| Synthetic 7680×4320, 30 fps | Zero displayed frames; startup timed out after 20 seconds |
| YouTube `yVLssFEqKmo`, itag 401, 3840×2160 at 60 fps | Same startup failure |
| YouTube `yVLssFEqKmo`, itag 571, 7680×4320 at 60 fps | Same startup failure |

All four attempts received a V4L2 resolution-change event. Chromium then
enumerated only `Q08C` for CAPTURE and reached image-processor setup without
producing a frame. This establishes decoder discovery and startup progress;
sustained hardware playback and hardware WebXR performance remain unmeasured.

The backport's `platform_sm8550.c` contains:

```c
{PIX_FMTS, DEC, AV1, FMT_NV12, FMT_TP10C, FMT_NV12C},
```

The sixth field is `step_or_mask`, so AV1 format enumeration advertises
only compressed `FMT_NV12C` (`Q08C`). Setting the input format to AV1 and
then running `v4l2-ctl --list-formats` reproduced this independently of
Chromium. A newly opened device defaults to H.264 and lists additional
formats, so listing formats before selecting AV1 misses the issue.
The earlier direct decoder probe explicitly selected linear NV12 and
bypassed this enumeration mismatch. The next integration test should add
linear NV12 to the AV1 capability mask, rebuild the temporary driver, and
repeat browser playback. That change was not made during this test.

For comparison, the previous Chromium 156 binary used `Dav1dVideoDecoder`
for these software baselines:

| Local AV1 input | Measured wall time | Video time advanced | Dropped / total frames | Mean Chromium CPU cores |
|---|---:|---:|---:|---:|
| Synthetic 4K60 | 30.19 s | 30.18 s | 8 / 1,811 (0.44%) | 1.97 |
| Synthetic 8K30 | 30.30 s | 30.30 s | 0 / 910 (0%) | 3.27 |
| Synthetic 8K60 | 30.31 s | 30.23 s | 81 / 1,815 (4.46%) | 6.46 |
| YouTube 4K60 | 60.41 s | 60.40 s | 8 / 3,626 (0.22%) | 2.52 |
| YouTube 8K60 | 60.69 s | 51.99 s | 362 / 3,121 (11.60%) | 6.88 |

The real 8K60 clip generated 80 waiting events during measurement. A
30.26-second software test of the real 4K60 clip through the project's
WebGL preview, using its two embedded eye meshes, reported zero drops
across 1,816 frames and 3.00 CPU cores. This was a desktop eye preview;
native immersive WebXR was not measured in this session.

Dropped-frame counts come from `getVideoPlaybackQuality()`. CPU cores are
summed Chromium process CPU seconds divided by elapsed wall time. These
short playback samples do not measure whole-device power consumption.

Test browser SHA-256:
`5b5cb5e0b1ac9c22b63edc26ad15ff59b63751754ec45333112aaadc0b8d176c`.
Temporary driver SHA-256:
`be6371e243489ed04350a257ca93636dc518a313a0653f9e7fa640535d077028`.
The installed stock driver file retained its original checksum.
After testing, a normal reboot restored the stock H.264/HEVC/VP9 formats
and the active `iris-driver-rebind.service`; AV1 was absent again.

## Check a new build

1. Install the archive with the matching launcher using `frame/install.sh`.
2. Inspect the loaded driver's formats:

   ```sh
   v4l2-ctl -d /dev/video-dec0 --list-formats-out
   ```

3. Open `chrome://media-internals`, then play a known local H.264 clip.
   Inspect its player entry for `V4L2VideoDecoder` and platform decoding.
   Check playback progress and dropped frames. `chrome://gpu` listing
   video decoding as enabled only establishes feature availability.
4. With an AV1-capable driver loaded and Chromium restarted, repeat with a
   small 8-bit AV1 clip before testing 4K60, 8K30 and WebXR. Check the actual
   decoder selection for each stream; successful playback can use software.

For logs, launch with:

```sh
chromium-xr --enable-logging=stderr \
  --vmodule='v4l2*=3,video_decoder_pipeline=3,gpu_mojo_media_client_linux=3'
```

To compare software playback, add `--disable-accelerated-video-decode`.
If supplying your own `--enable-features`, include both `OpenXR` and
`AcceleratedVideoDecoder` in that list.
