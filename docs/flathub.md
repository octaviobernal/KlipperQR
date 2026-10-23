<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Submitting KlipperQR to Flathub (issue #34)

Everything that can be prepared locally is done. The steps below are for the
maintainer, because they act on GitHub outside this repository.

## Status of the acceptance criteria

| Criterion | Status |
| --- | --- |
| App id fits `io.github.octaviobernal.*` | Maintainer must confirm (step 1). `gh` is logged in as `octaviobernal`, which matches the id. |
| Manifest builds with pinned sources, minimal permissions | Done: `flatpak/flathub/io.github.octaviobernal.KlipperQR.yaml` (git tag + commit, segno wheel with sha256, Wayland/X11 fallback/ipc/dri, no network). The commit hash is a placeholder until the tag exists (step 3). |
| `flatpak-builder-lint` | Manifest: no findings (both manifests). Built repo: only the two screenshot findings below. |
| Pull request to `flathub/flathub` `new-pr` | Maintainer (step 5). |
| Review feedback tracked on the issue | Maintainer / later. |

### Lint results for the built repo

Command (the Flatpak linter, `org.flatpak.Builder`):
`flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo <repo-dir>`

Two findings remain and are expected for a local build; no code fix exists:

- `appstream-external-screenshot-url` and
  `appstream-screenshots-not-mirrored-in-ostree`: Flathub's own build service
  downloads the screenshots and mirrors them to `dl.flathub.org/media`; a local
  build never does. They go away on Flathub as long as the screenshot URLs
  resolve at build time, so the tag `v1.0.0` must be pushed before the PR is
  built.

## Maintainer steps

1. Read https://docs.flathub.org/docs/for-app-authors/requirements (app id
   rules for `io.github.<user>`) and confirm that GitHub user `octaviobernal`
   and this repository may use `io.github.octaviobernal.KlipperQR`. Record the
   outcome as a comment on issue #34. If the id does not fit, stop and ask for
   an id change first (it appears in many files, see issue #15).
2. Commit and push the current state to `main`. Wait for CI to be green.
3. Create and push the release tag, then put its commit in the Flathub manifest:
   ```sh
   git tag -a v1.0.0 -m "KlipperQR 1.0.0"
   git push origin v1.0.0
   git rev-parse 'v1.0.0^{commit}'   # paste into `commit:` in flatpak/flathub/*.yaml
   ```
   The metainfo already lists release 1.0.0 and its screenshot URLs point at
   the `v1.0.0` tag, so the tag must contain the current metainfo. If you must
   change files after tagging, move to a new version instead of rewriting the tag.
4. Check the network-dependent items once the tag is pushed:
   `appstreamcli validate data/io.github.octaviobernal.KlipperQR.metainfo.xml`
   (without `--no-net`), and build the Flathub manifest locally:
   `flatpak-builder --user --force-clean --install-deps-from=flathub build-dir flatpak/flathub/io.github.octaviobernal.KlipperQR.yaml`.
5. Follow https://docs.flathub.org/docs/for-app-authors/submission : fork
   `flathub/flathub` (uncheck "copy master branch only"), create a branch from
   `new-pr`, add only `io.github.octaviobernal.KlipperQR.yaml` (copy of
   `flatpak/flathub/...yaml`) at the repo root, and open a pull request against
   `new-pr`. Fill in the PR checklist. Paste the PR link in issue #34.
6. Answer review feedback as comments on issue #34. A reviewer may ask for
   justification of `--device=dri` (needed by Qt Quick rendering; see
   docs/flatpak.md) or a `flathub.json`; none is needed now.

## Notes on the manifest

- Two manifests exist on purpose. `flatpak/io.github.octaviobernal.KlipperQR.yaml`
  builds the local checkout (used by CI and development). The Flathub copy
  differs only in the final source (`type: git`, tag + commit) because Flathub
  rejects `type: dir`. `tests/test_flathub.py` fails if they drift apart.
- Flathub builds have no network except for the declared sources. segno is a
  pinned wheel with sha256; PySide6 comes from `io.qt.PySide.BaseApp`.
- License `GPL-3.0-or-later` and OARS rating are in the metainfo.
