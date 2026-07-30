# Appliance patches for the deployed v1.2.3 add-on

This branch tracks appliance-specific fixes that are **live on Aryan's Kodi
HTPC** but have no home in canonical `main`, because the deployed add-on is the
divergent v1.2.3 tree while `main` carries v2.0.0-beta.2.

`docs/NZBDAV_MIGRATION.md` in `aryan-j/kodi-htpc-setup` forbids copying the live
profile tree into this repository, so the fixes are tracked as **replayable
patches against recorded baselines** rather than as a source snapshot. Per
`docs/OPERATING_MODEL.md` §6, appliance customization belongs on a maintained
appliance branch — this one.

**This branch must never be merged into `main`.** It exists to make the live
system reproducible and to give the v2 migration a rollback anchor.

## Why these fixes exist

Trakt scrobbling from NZBDav playback was completely non-functional, so Kodi's
"Continue Watching" row was permanently empty, and in-episode resume always
restarted from zero. Four defects, all on the NZBDav side:

| # | Defect | File |
| --- | --- | --- |
| 1 | `PlayerInfoString` was written without TMDb Helper's required `TMDbHelper.` window-property prefix, so its scrobbler never saw the playback identity | `resources/lib/resolver.py` |
| 2 | `tmdb_id` was sent as a string; Trakt rejected every scrobble with HTTP 422. The failure was silent because the shared request helper deliberately does not log 4xx bodies | `resources/lib/resolver.py` |
| 3 | `onPlayBackSeek` stored Kodi's **milliseconds** as seconds, corrupting the retry/resume position by 1000x | `service.py` |
| 4 | No resume support: each play mints a fresh proxy token on an ephemeral port, so Kodi keys its resume bookmark to a URL it never sees again. A pre-existing workaround also deletes those bookmarks before every play | `service.py`, `resources/lib/resolver.py` |

Defect 3 is **not appliance-specific** and is fixed against canonical source on
`agent/fix-seek-callback-milliseconds` (PR #2). It appears in patch 0002 only
because the live tree needed it too.

Defect 4 is a **stopgap**. Canonical `main` already ships a proper resume
implementation (`resources/lib/resume_store.py`, `nzbdav.resume_key` /
`nzbdav.resume_offset` IPC, near-end pruning). Migrating to v2 supersedes the
appliance resume code, which should then be deleted rather than ported.

## Verification

Each patch was verified by applying it to its recorded baseline and confirming
the result is byte-identical to the live working file.

| File | Baseline SHA-256 (pre-fix) | Result SHA-256 (live, working) |
| --- | --- | --- |
| `resources/lib/resolver.py` | `3f72020089d35db83957dcad32880fd87ad8b0bb2d1534a958cc145e7e53cb1f` | `ba259284a2b18386f1ccce64ed08931c93cfefedb1fd9b2dad8daa0cc798416f` |
| `service.py` | `8b768130a54964ff7a74ac218eeaee5801b36bec13bc6e75f71aa55554f01bff` | `633ffad90297c0b69a6c7f63f06a614ae29059652085eb7adf8bc55fca6af99e` |

Both baselines predate this work and already contained an earlier untracked
live hotfix, so they are recorded by hash rather than assumed reproducible from
any tagged release.

## Live validation (2026-07-30)

- Trakt accepted a live scrobble: `/users/me/watching` returned the episode with
  integer `tmdb: 94997`; after stop, `/sync/playback/episodes` reported
  `progress: 18.57`.
- Seek logging changed from `-> 1379045s` to `822s` / `1049s` / `1404s` on a
  4238-second episode.
- Resume from a stored position confirmed working by the operator.
- **Untested / known gap:** Kodi's "Play from beginning" is not honoured. The
  add-on is registered as a TMDb Helper *script* player
  (`is_resolvable: false`, `executebuiltin://RunScript(...)`), so Kodi never
  resolves a URL for it and the start offset it computes is discarded when the
  add-on starts its own playback.

## Applying

Patches apply from the add-on root (the directory containing `addon.xml`):

```bash
patch -p0 resources/lib/resolver.py < appliance/patches/0001-resolver-trakt-scrobble-and-resume.patch
patch -p0 service.py < appliance/patches/0002-service-seek-units-and-resume-store.patch
```

Confirm the resulting hashes match the table above before deploying.

## Rollback

A verified full snapshot of the working add-on tree and its add-on data lives
outside every repository at:

```
D:\Kodi-Backups\nzbdav-live-v1.2.3-20260730-1450\
```

`plugin.video.nzbdav-live.tar.gz` is the add-on tree with bytecode excluded;
`addon-data-SECRETS-LOCAL-ONLY.tar.gz` carries operator settings and secrets and
must never be committed, attached to a PR, or included in a diagnostic bundle.
`SHA256SUMS.txt` verifies both.

Note the snapshot intentionally includes `resources/settings - Copy.xml` for
exact-restore fidelity. That stray file must be excluded from any build artifact
or published zip.
