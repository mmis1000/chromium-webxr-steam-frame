# Iris hardware video decoding

Steam Frame exposes Qualcomm Iris through V4L2. The recipe enables that
backend and the launcher adds `AcceleratedVideoDecoder` to its existing
feature list. Chromium's software decoders remain available for fallback.

## Build settings and patches

```gn
use_v4l2_codec = true
use_vaapi = false
use_av1_hw_decoder = true
use_v4l2_stateless_av1_decoder = false
```

Patch 0002 passes `config.coded_size()` when configuring the compressed
OUTPUT queue. Iris accepted the previous zero-sized format but rejected
subsequent input-buffer allocation with `EINVAL`.

Patch 0003 introduces `use_v4l2_stateless_av1_decoder`. Its default preserves
the existing stateless behavior when V4L2 and hardware AV1 are enabled.
This recipe disables it because its Linux sysroot lacks the stateless AV1
request controls. The flag gates the stateless delegate, test tool, control
logging and profile-discovery entry. Stateful `AV01` and its profile mapping
remain enabled. Missing AV1 profile constants use Linux UAPI values.

Patch 0004 handles CAPTURE buffers with no payload beyond `data_offset`.
Iris returned these between AV1 display frames; presenting their previous
contents caused blinking and inflated decoded/dropped frame counts.
The decoder recycles these buffers and drains the OUTPUT queue without
presenting a frame. LAST-buffer handling still runs first, so the existing
flush/resolution-change behavior is preserved.

## Driver requirements

The stock drivers tested on SteamOS 0.5.6 and 0.5.7 exposed H.264, HEVC and
VP9. Hardware AV1 requires a driver exposing `AV01` and a supported CAPTURE
format, such as linear `NV12`. The separately maintained
[Iris AV1 backport](https://github.com/mmis1000/steamframe-iris-av1-poc)
provided that support for the recorded AV1 tests. This branch installs no
kernel module.

When AV1 is absent from the driver, Chromium uses dav1d. Restart Chromium
after changing the loaded driver to refresh codec discovery. To force
software decoding for a browser session, pass
`--disable-accelerated-video-decode` to the launcher.

## Validation

These runtime observations used custom Chromium 156 or 157 builds with the
same decoding changes. The branch retains upstream's Chromium 158.0.8127.2
pin. All four patches apply and reverse-check against that release; the
158 adaptation changes patch context for its codec-control map initializer.
A full Chromium 158 build and device playback have not been run for this
branch.

| Configuration | Observed result |
| --- | --- |
| Chromium 156, stock Iris, H.264 1080p60 | V4L2 decoding; 682 frames with zero drops |
| Chromium 156, corrected AV1 driver, empty-buffer fix | 384 empty buffers skipped; subsequent 607 frames had zero drops; wearer confirmed blinking was gone |
| Chromium 156, corrected AV1 driver, real 4K60 AV1 | 59.88 presented frames/s over 60.39 s; 8 drops out of 3,625 frames |
| Chromium 156, corrected AV1 driver, synthetic 8K30 AV1 | 30.01 presented frames/s over 121.04 s; zero drops out of 3,632 frames |
| Chromium 156, corrected AV1 driver, real 8K60 AV1 | Approximately half-speed playback; 257 drops out of 3,576 frames |
| Chromium 157.0.8103.15, SteamOS 0.5.7, H.264 1080p60 | V4L2 decoding; 321 frames with zero drops in the post-install sample |
| Chromium 157.0.8103.15, SteamOS 0.5.7, YouTube 4K VP9 | V4L2 selected during native WebXR with both eye views; initial sample had synchronization seeks and 118 drops out of 620 frames |

The AV1 driver tests used kernel `6.18.0-g83913f38113c`; the later stock-driver
tests used `7.2.0-g9a8c8ea46950`. HEVC, 10-bit/HDR and film grain are outside
this validation record. The measured 8K60 throughput remains below real time.
These results establish decoder selection and the empty-buffer fix, with
performance recorded separately for each tested stream.

## Check the recipe

```sh
python3 build/check-patches.py
bash -n build/build.sh
bash -n frame/chromium-xr
```

The checker downloads the source files touched by the patches from the
pinned Chromium tag, applies the patches in order, and checks the reverse
operation used by the build script when resuming. The Check decoding recipe
workflow runs these checks for pushes and pull requests.

On a device, inspect the player's decoder in `chrome://media-internals`
while playing a known clip. Hardware playback reports `V4L2VideoDecoder`
and `kIsPlatformVideoDecoder: true`. Check actual playback progress and
dropped frames as well; individual streams can select software decoding.

## Relationship to upstream draft #6

[Draft #6](https://github.com/saphid/chromium-webxr-steam-frame/pull/6),
reviewed at commit `9ff0640ab890f059045f27bbd9c81ab5b258fae6`, already enables
V4L2, disables VA-API, adds the launcher's acceleration feature and supplies
the coded input dimensions. Its HEVC patch also adds HEVC access-unit
handling, larger input buffers above 4K, decode-failure reporting and
restrictions for unsupported 10-bit output.

This standalone branch starts from upstream `main` at
`0f6bad3b265984e0530cd0e8336d89ae745dcb91`. Its distinct additions relative
to the draft are patch 0003's stateful AV1 build support and patch 0004's
empty-CAPTURE-buffer fix. It retains the common V4L2 setup and coded-size
patch so it can be reviewed against `main` independently.

To integrate the additions into draft #6:

1. Keep the draft's existing V4L2/VA-API settings and launcher feature.
2. Keep its combined HEVC/coded-size patch in place of this branch's 0002.
3. Add patch 0003 and the `use_av1_hw_decoder = true` and
   `use_v4l2_stateless_av1_decoder = false` build settings.
4. Add patch 0004 for the blinking fix.

On November 9, the draft's HEVC patch followed by patches 0003 and 0004
applied to Chromium 158.0.8127.2. Every patch passed its reverse check after
the full combined stack was applied. The standalone coded-size patch
duplicates the draft's fix and must be omitted from that combined stack.
This compatibility check covers patch application; device measurements
above come from the previously tested 156/157 builds.
