# Patches

Local changes applied on top of the Chromium release that `build/build.sh`
builds (`CHROMIUM_VERSION`), in file-name order.

- `0001-xr-sandbox-allow-getsockopt-SO_PEERCRED.patch`: lets the XR process
  call `getsockopt(SOL_SOCKET, SO_PEERCRED)`, which SteamVR's OpenXR runtime
  needs. See [docs/technical-notes.md](../docs/technical-notes.md).

- `0002-v4l2-stateful-set-coded-size.patch`: passes the configured coded
  dimensions to the compressed input queue. Iris needs them before allocating
  its input buffers.
- `0003-v4l2-stateful-av1-build.patch`: separates stateful AV1 support from
  compilation of the stateless AV1 request API, and supplies missing AV1
  profile constants for older Linux sysroot headers. The patch is adapted
  to the pinned Chromium 158 source's codec-control map initializer.
- `0004-v4l2-stateful-skip-empty-capture.patch`: recycles empty CAPTURE
  buffers without displaying stale pixels. This fixes the blinking observed
  during AV1 playback; LAST-buffer handling retains its existing priority.

Run `python3 build/check-patches.py` to check the full patch stack against
the pinned Chromium sources. See [hardware decoding](../docs/video-decoding.md)
for the driver requirements and device validation record.

These patches modify Chromium source and are under
[Chromium's BSD-style license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE),
Copyright The Chromium Authors.
