# Dynaamx build of Libredesk

This fork builds [Libredesk](https://github.com/abhinavxd/libredesk) with a few changes for
Dynaamx's support desk (support.dynaamx.tech, help.dynaamx.tech) and publishes the image
`ghcr.io/aumair-malik/dynaamx-helpdesk:<version>-dynaamx.<revision>` (for example
`v2.9.2-dynaamx.1`), where `<revision>` is the number in [`REVISION`](REVISION). The
deployment itself (compose file, Coolify project, migration notes) lives in the private
`dynaamx-self-hosted-deployments` repo.

## Changes

All in [`apply.py`](apply.py), run against an untouched Libredesk release:

1. **No "Powered by" credit anywhere**: agent sign-in page, chat widget (and its preview in
   the inbox settings, with the "Show powered by" switch, which no longer does anything),
   help center footers (Classic and Docs themes), survey page, and the footer of every email.
2. **Every time zone in the dropdowns** (general settings and teams): the zones of the tzdata
   the image installs (about 420, upstream lists 35), labelled with today's UTC offset, UTC
   first, then by offset. Upstream's values are kept, so saved settings still match.
3. **Base image** `alpine:3.24` in place of upstream's `alpine:3.18`, which is end of life.

Nothing else differs: the version (`--version`), database schema and upgrades are upstream's.

## How it builds

[`.github/workflows/dynaamx-image.yml`](../.github/workflows/dynaamx-image.yml) runs daily and
on demand (Actions → Dynaamx image → Run workflow, optionally with a version):

1. takes Libredesk's latest release (or the version given) and stops if its image exists;
2. clones it, runs `apply.py`, which fails the build if any change no longer applies cleanly
   or any credit is left;
3. builds the frontend and the binary with upstream's Makefile, then the image from
   [`Dockerfile`](Dockerfile), and tests it (version, every time zone loads, `wget` present);
4. pushes the exact source as a tag of the same name (Libredesk is AGPL-3.0: the source
   of what runs is public) and the image to GHCR.

Building never deploys. To update the server, change the Libredesk image in Coolify to the
new tag and restart.

## When a build fails

Usually a new Libredesk release moved something `apply.py` edits. Its error names the file
and the edit; compare that file with the release, adjust the pattern in `apply.py`, and run
the workflow again for that version.

## Adding a change

Add a step to `apply.py` (an exact edit that must match, plus a check if it can drift), run
it on a clean checkout (`python3 dynaamx/apply.py <src> --tzdata /usr/share/zoneinfo`),
build, raise the number in `REVISION`, commit, then run the workflow. Every image tag is one
fixed build; nothing is ever rebuilt under an existing tag. Keep changes small: each one has
to be carried into every new release. Never put secrets in this repository; it is public.
