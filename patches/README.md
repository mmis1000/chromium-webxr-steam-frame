# Patches

Local changes applied on top of the Chromium release that `build/build.sh`
builds (`CHROMIUM_VERSION`), in file-name order.

- `0001-xr-sandbox-allow-getsockopt-SO_PEERCRED.patch`: lets the XR process
  call `getsockopt(SOL_SOCKET, SO_PEERCRED)`, which SteamVR's OpenXR runtime
  needs. See [docs/technical-notes.md](../docs/technical-notes.md).
- `0002-v4l2-stateful-set-coded-size.patch`: passes the video's coded size
  when configuring the compressed input queue. Iris rejects input-buffer
  allocation after Chromium's previous `0 x 0` configuration.
- `0003-v4l2-stateful-av1-build.patch`: separates stateless AV1 compilation
  from stateful AV1 support and supplies the AV1 profile constants missing
  from older Linux sysroot headers. The build enables stateful AV1 and
  disables the stateless AV1 path, whose request controls are absent from
  that sysroot. Runtime codec discovery still follows the loaded driver.

The patches target the pinned Chromium 157 release. Patch 0002 was also
tested in Chromium 156 on Steam Frame. See
[video-decoding.md](../docs/video-decoding.md) for validation details.

These patches modify Chromium source and are under
[Chromium's BSD-style license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE),
Copyright The Chromium Authors.
