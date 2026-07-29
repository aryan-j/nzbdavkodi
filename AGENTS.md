# NZB-DAV Kodi agent contract

This file is the short mandatory contract. Load referenced documentation only
when the affected behavior triggers it.

## Non-negotiable invariants

- Runtime add-on code stays pure Python and Python 3.8 compatible: no walrus,
  `match`, `str.removeprefix`, compiled dependencies, or C extensions.
- Every resolver path calls `xbmcplugin.setResolvedUrl(...)`: `True` on success,
  `False` on cancellation, timeout, and failure.
- Kodi polling uses `xbmc.Monitor.waitForAbort()`, never `time.sleep()`.
- Stream proxy and WebDAV behavior preserve HTTP Range requests and seeking.
- Non-MP4 pass-through remains the default unless settings explicitly force
  remux. ffmpeg stays optional and failures degrade gracefully.
- Settings are defined in `resources/settings.xml` and read through
  `xbmcaddon.Addon().getSetting(...)`; preserve safe service-thread access.
- Tests rely on `tests/conftest.py` installing Kodi mocks before add-on imports.
- Use shared HTTP and notification helpers in `http_util.py`.
- Do not edit vendored PTT unless fixing compatibility.
- Never commit API keys, WebDAV credentials, Kodi/crash logs, copied device
  artifacts, generated `site/`, or local runtime state.

## Default change flow

1. Search for the affected route and existing tests; do not load large
   references wholesale.
2. Follow existing Kodi mock, settings, HTTP-helper, and player-install patterns.
3. Make the smallest focused change and add focused success/failure tests.
4. Run the narrowest useful test first, then the required pre-publication gate.
5. Report only material behavior, validation, compatibility, and remaining risk.

Before commit or push run `just lint` and `just test`. If lint finds formatting
issues, run `just lint-fix`, then rerun lint. Use `just ci` when the change has
broad compatibility or release risk.

## Reference triggers

| Trigger | Read/search |
| --- | --- |
| Outstanding architecture work | Relevant headings in `TODO.md` |
| Proxy, Range, remux, MP4, seeking | `docs/proxy-architecture.md`; search relevant headings only |
| Fallback streams or cutover | Relevant headings in `FALLBACK_INFO.md` and `docs-site/how-it-works/fallback-cutover.md` |
| Search/filter/indexer behavior | Relevant `docs-site/` feature/how-it-works page |
| Settings or user documentation | `docs-site/reference/settings.md`; search setting ID first |
| Release | Release section below and relevant version heading in `CHANGELOG.md`; never load the full changelog |
| PR review/comments | `python3 scripts/pr_agent_context.py --json`, the preferred unified agent context packet |
| Live CoreELEC deployment/debugging | Live operations section below |

Large changelogs, architecture histories, generated docs, logs, and fixtures are
search-first references. Bound command output by file, pattern, time range,
count, or tail; prefer failing cases over successful trace noise.

For compatibility, use `fetch_comments.py` directly when a skill or workflow expects that helper by name.

## Repository routes

- Router: `repo/plugin.video.nzbdav/resources/lib/router.py`
- Search: `hydra.py`, `prowlarr.py`
- Filtering/ranking: `filter.py`
- Submit/poll/resolve: `resolver.py`
- WebDAV: `webdav.py`
- Proxy: `stream_proxy.py`
- Player installation: `player_installer.py`
- Settings: `repo/plugin.video.nzbdav/resources/settings.xml`
- Tests/mocks: `tests/`, `tests/conftest.py`
- Documentation source: `docs-site/`

## Focused behavior gates

- Resolver changes cover success, cancellation, timeout, and failure.
- Submit/poll/WebDAV/proxy handoff changes check fallback behavior.
- Proxy changes check Range/status handling, pass-through defaults, optional
  ffmpeg failure, and affected MP4/subtitle/large-file behavior.
- Search changes keep NZBHydra2 and Prowlarr aligned where practical and test
  ranking, filtering, and edge-case titles.
- Player installation preserves profile containment and schema-version
  backup/preservation unless tests deliberately revise the contract.

## Commands

```text
just test          focused/full tests
just lint          ruff + black + pylint + vermin
just lint-fix      apply formatting fixes
just ci            lint + tests + Python 3.8 compile gate
just release       build add-on zip
just docs          strict documentation build
just extreme-tests end-to-end fault recovery
```

Use `just deploy-addon` only for an authorized live deployment. Other commands
can be discovered with `just --list`; do not load a command catalog by default.

## Releases

Only bump `repo/plugin.video.nzbdav/addon.xml`. Update the user-facing README,
the relevant repo `CHANGELOG.md` version section, and the Kodi-visible
`repo/plugin.video.nzbdav/changelog.txt` summary. Run lint and tests before
publishing. The Release workflow builds the zip; the external Appz4Fun Kodi
repository republishes it. Documentation publishes through Pages and does not
publish add-on metadata.

## Live operations

Preserve useful Kodi log/crash evidence before restart when practical. Agents
may restart a crashed, hung, or deployment-test Kodi instance on
`root@coreelec.local`; do not turn a diagnostic request into deployment.
Use bounded remote output such as `tail -200`. Keep copied logs outside Git.
