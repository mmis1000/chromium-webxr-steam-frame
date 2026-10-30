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
| AV1 | Driver exposing `AV01` | Direct driver tests passed; browser integration pending |

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
- The AV1 build changes compiled successfully for ARM64 against the cached
  Chromium 156 tree: stateful decoder, stateless backend, decoder setup and
  codec utilities. The port includes the AV1 logging guards present in 157.
  This checks the source changes against the older Linux sysroot; it does
  not establish browser playback with AV1.
- The recipe targets Chromium 157.0.8103.15. Full compilation and on-device
  playback of that exact release remain required.
- All three patches applied and passed their reverse checks against the
  pinned 157 sources. Launcher checks preserved the WebXR and decoding
  features, a URL containing spaces and the software-decoding override.

Run `python3 build/check-patches.py` to repeat the source check. An optional
version argument checks another release. The Check recipe workflow runs
this check and shell syntax validation on pushes and pull requests.

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
