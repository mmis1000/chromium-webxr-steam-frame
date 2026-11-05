# Chromium with WebXR for the Steam Frame

A build recipe and installer for **Chromium with immersive WebXR on Valve's
Steam Frame** headset. Press the
**Enter VR** button on a WebXR site and it opens in the headset, through
SteamVR, as a full VR experience.

Chromium 157 includes upstream Linux OpenXR support. On SteamOS 0.5.7,
`--enable-features=OpenXR` enables native WebXR with the XR service's sandbox
active. This fork adds V4L2 hardware video decoding for the Frame's Iris
driver and installs Chromium as a normal app in your Steam library.

## What you can do with it

The web has a lot of VR content that only needs a browser:

- **360° and 3D video.** Travel, nature, concerts, sports and documentaries
  from players that support WebXR, shown around you instead of in a flat
  window.
- **Games and toys.** WebXR games and experiments made with
  [three.js](https://threejs.org/examples/?q=webxr),
  [A-Frame](https://aframe.io/) or [Babylon.js](https://www.babylonjs.com/),
  with nothing to install.
- **Learning.** Virtual museum tours, space and anatomy explorers, and other
  educational experiences built for the web.
- **Art and music.** Painting, sculpting and music toys that run in a page.
- **Building WebXR sites.** Test your own WebXR app on real headset hardware
  from a normal URL, with Chromium's DevTools.

## Status

On November 5, 2026, the published **157.0.8103.15** build was installed on
SteamOS **0.5.7** (build `20261103.6153824`). Native WebXR produced both eye
views with the XR service's seccomp filter active. H.264 1080p60 and a
YouTube 3840 × 2160 VP9 stream selected `V4L2VideoDecoder`. AV1 used dav1d
because the loaded stock driver did not advertise AV1. See the
[validation record](docs/video-decoding.md#validation-record) for details.

Earlier tests on a Steam Frame (SteamOS 0.3.0, build 20260922.6101926,
SteamVR 2.17.10) with Chromium **156.0.8071.0**, built for arm64:

| | |
|---|---|
| `isSessionSupported("immersive-vr")` | `true` |
| [WebXR Samples](https://immersive-web.github.io/webxr-samples/) Immersive VR Session | shows its scene in the headset |
| three.js [stereo 360 video](https://threejs.org/examples/webxr_vr_video.html) | plays in 3D |
| Launch from the Steam library | opens as its own panel, like any app; WebXR renders in the headset |
| Controllers inside WebXR pages | tracked pose every frame; squeeze events and button state reach the page (trigger, thumbstick and left controller not tested) |
| Frame rate | 72 fps, every frame 13.9–14 ms over 16 s (simple scene); SteamVR dropped frames only at startup |

The build targets Chromium 157.0.8103.15, which has the upstream Linux
OpenXR changes merged. The launcher requires SteamOS 0.5.7 or newer and
keeps the XR service's seccomp filter enabled.

This fork enables **V4L2 hardware video decoding** through the Frame's Iris
driver, including the input-size fix verified with H.264 1080p60 and WebXR
on Chromium 156. Hardware AV1 is compiled in for use with an AV1-capable
driver, such as the experimental
[Iris AV1 backport](https://github.com/mmis1000/steamframe-iris-av1-poc).
The stock driver tested on SteamOS 0.5.6 exposes H.264, HEVC and VP9;
AV1 uses software decoding there. See
[decoding support and validation](docs/video-decoding.md) for tested results
and the AV1 driver requirements.

This is an unofficial, experimental build. See [Limitations](#limitations)
before you use it for anything other than VR sites.

## Requirements

- A Steam Frame running SteamOS 0.5.7 or newer with SteamVR, and a way to run
  commands on it: the terminal in Desktop Mode, or SSH.
- To build: an **x86-64 Linux machine** with about **90 GB free disk**, git,
  Python 3, tmux (or another way to keep a long job running) and a few
  hours. No root access is needed. The first build took about 9.5 hours on
  a 6-core, 12-thread desktop CPU; rebuilds take minutes.

## Build

On the Linux build machine:

```sh
git clone https://github.com/mmis1000/chromium-webxr-steam-frame
cd chromium-webxr-steam-frame
mkdir -p ~/chromium-xr
tmux new -d -s chromium-xr 'build/build.sh > ~/chromium-xr/build.log 2>&1'
```

`build.sh` fetches Chromium with the Linux OpenXR changes, applies the patches
in [`patches/`](patches), cross-compiles for arm64 and packs the result into
`~/chromium-xr/chromium-xr-arm64.tar.xz` (about 145 MB).

- Follow progress with `tail -F ~/chromium-xr/stage` (milestones) or
  `tail -F ~/chromium-xr/build.log` (everything).
- If it stops (reboot, full disk, network), run the same command again. It
  picks up where it left off.
- To build on another disk, set `CHROMIUM_XR_DIR` and use that directory
  in place of `~/chromium-xr` in the commands above, including the log path.
- It stops itself if free disk space drops below 12 GB.

### Build on GitHub Actions

Instead of a local machine, a fork of this repo can build on GitHub's free
runners. In the **Actions** tab, run the **Build** workflow; leave the version
empty to build the one pinned in `build.sh`. When it's done, download
`chromium-xr-arm64.tar.xz` from the run's artifacts. Pushing a tag that starts
with `v` (for example `v157.0.8088.0-1`) also publishes it as a release.

A first build takes more than a day on a free runner, and a job may only run
for 6 hours. So the workflow runs in up to ten parts. Each part builds for
about 5 hours and passes the build tree on to the next as an artifact (about
10–20 GB). This keeps artifact storage free only in a public repository.

## Install on the Frame

Copy the tarball and this repo to the Frame, then run the installer there.
For example, over SSH from the build machine (replace `steamframe` with your
Frame's hostname or IP address):

```sh
scp ~/chromium-xr/chromium-xr-arm64.tar.xz steamos@steamframe:
ssh steamos@steamframe
git clone https://github.com/saphid/chromium-webxr-steam-frame
chromium-webxr-steam-frame/frame/install.sh ~/chromium-xr-arm64.tar.xz
```

The installer:

- unpacks the build into `~/chromium-xr`, after checking the new binary runs;
- installs the `chromium-xr` launcher in `~/.local/bin`;
- adds **Chromium XR** to the Desktop Mode app menu;
- adds **Chromium XR** to your Steam library, without restarting Steam.

Run it again with a newer tarball to update. Your profile
(`~/.config/chromium-xr`) and the Steam shortcut are kept. You can delete
the repo clone afterwards; the installer keeps what it needs to uninstall.

If the Steam shortcut can't be added automatically, add it by hand: in
Desktop Mode, open Steam, choose **Games → Add a Non-Steam Game to My
Library**, and pick Chromium XR.

## Use it

1. Open **Chromium XR** from your Steam library. It appears as a panel in
   the headset.
2. Go to a WebXR site, for example the
   [WebXR Samples](https://immersive-web.github.io/webxr-samples/).
3. Press the site's **Enter VR** button.
4. Chromium asks **Allow VR?** in the browser panel. Choose *Allow this time*
   or *Allow while visiting the site*.
5. To leave VR, use the site's exit button or the Steam button.

The first time you launch it, Steam may show an **External Controller
Translation** notice. It's only information about controller button icons;
choose OK.

From a terminal on the Frame, `chromium-xr https://example.com` opens a
page directly.

## Limitations

- **GPU sandbox status.** The XR service and renderer seccomp filters work
  on SteamOS 0.5.7. The GPU process can still report unsandboxed on the Frame;
  removing the old global filter-disable flag does not change that separate
  status. See [docs/technical-notes.md](docs/technical-notes.md).
- **Saved passwords aren't encrypted.** The launcher uses
  `--password-store=basic` so startup doesn't stop at a keyring prompt, so
  passwords you save are stored unencrypted in `~/.config/chromium-xr`.
- **No automatic updates on the Frame.** It won't get Chromium security fixes
  until you install a newer build. The repo builds new Chromium releases by
  itself (see [Updating](#updating)), but you still have to install them.
- **No controller vibration.** SteamVR reports no haptic actuators to the page.
- **No DRM video.** There's no Widevine, so paid streaming services that
  need it won't play.
- **One window at a time per profile.** If Chromium XR is already open,
  launching it again opens the page in the existing window.
- **Not a default browser.** It works as one (the desktop entry registers
  for web links), but for the reasons above it's better kept for VR.

## Remove it

```sh
~/.local/share/chromium-xr/uninstall.sh                   # keeps your profile
~/.local/share/chromium-xr/uninstall.sh --remove-profile  # also deletes settings and logins
```

This removes the build, the launcher, the menu entry and the Steam shortcut.

## Updating

To publish an existing successful manual **Build** run, run **Publish
completed build** with its run ID. To publish a build still in progress,
set the repository Actions variable `RELEASE_BUILD_RUN_ID` to that run ID;
publication runs when that specific build succeeds. It uses the existing
archive and tags the exact build commit as `build-RUN_ID`, with a SHA-256
checksum attached. Other manual builds remain artifact-only.

The build pins one Chromium release (`CHROMIUM_VERSION` in
[`build/build.sh`](build/build.sh)). On GitHub, the **Bump Chromium** workflow
checks once a week for a newer Linux release on Stable (on Beta until Stable
reaches Chromium 157). If the patch in [`patches/`](patches) still applies,
it updates the pin, tags it and starts a build that publishes a release; if
not, the run fails so the patch can be updated by hand. In a fork, enable
scheduled workflows in the **Actions** tab first.

To build a newer
one, set `CHROMIUM_VERSION` to any Chromium release tag when you run the
build, as in `CHROMIUM_VERSION=<version> build/build.sh`, or enter it
when you run the GitHub workflow. The script fetches it, syncs, re-applies the
local patch and rebuilds. A newer release may need the patch in
[`patches/`](patches) updated. Then install the new tarball on the Frame as
above.

## How it works

- **Chromium changes.** [CL 8441736](https://chromium-review.googlesource.com/c/chromium/src/+/8441736)
  (a sandboxed XR process on Linux) and
  [CL 8132979](https://chromium-review.googlesource.com/c/chromium/src/+/8132979)
  (the OpenXR device provider on Linux), tracked in Chromium
  [issue 506004811](https://issues.chromium.org/issues/506004811). Both have
  merged and ship from Chromium 157. The OpenXR device is behind
  `--enable-features=OpenXR`, which the launcher passes.
- **SteamVR compatibility.** SteamOS 0.5.7's runtime works with Chromium's
  XR sandbox. Valve removed the socket credential check and changed its
  process-ID exchange, addressing the earlier failures tracked in
  [utzcoz/chromium-webxr-linux#7](https://github.com/utzcoz/chromium-webxr-linux/issues/7).
  The published 157.0.8103.15 archive retains the narrow `SO_PEERCRED`
  allowance from patch 0001; the launcher no longer disables seccomp.
- **Steam integration.** `frame/steam-shortcut.py` adds the shortcut through
  the Steam client's local DevTools port, the same API the Steam UI uses.
  Steam runs each app as its own panel, so Chromium gets one too.

More detail, including the history of the sandbox workaround, is in
[docs/technical-notes.md](docs/technical-notes.md).

## Related work

- [utzcoz/chromium-webxr-linux](https://github.com/utzcoz/chromium-webxr-linux):
  a fuller patch series for WebXR over OpenXR on Linux desktops, including
  the in-headset permission UI and crash fixes, tested with
  [Monado](https://monado.dev/). If you're on an x86-64 Linux PC rather than
  the Steam Frame, start there.
- [Chromium issue 506004811](https://issues.chromium.org/issues/506004811):
  upstream tracking for WebXR on Linux.

## License

The scripts in this repo are under the [BSD 3-Clause License](LICENSE). The
patch in [`patches/`](patches) modifies Chromium and is under
[Chromium's license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE).
Chromium is a trademark of Google LLC; this project is not affiliated with
Google or Valve.
