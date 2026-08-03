# SPDX-License-Identifier: GPL-3.0-or-later

"""Focused tests for terminal-failure candidate rotation."""

from unittest.mock import MagicMock, patch


def test_selection_retry_loader_preserves_ranked_alternates_and_isolated_copies():
    from resources.lib.router_play import _selection_retry_candidate_loader

    selected = {"title": "Primary", "link": "http://indexer/primary"}
    alternate = {"title": "Alternate", "link": "http://indexer/alternate"}
    rows = [
        selected,
        alternate,
        {"title": "No link"},
        {"title": "Duplicate", "link": alternate["link"]},
        {"title": "Last", "link": "http://indexer/last"},
    ]

    loader = _selection_retry_candidate_loader(selected, rows)

    assert [row["link"] for row in loader()] == [
        "http://indexer/alternate",
        "http://indexer/last",
    ]
    loaded = loader()
    loaded[0]["title"] = "mutated"
    assert alternate["title"] == "Alternate"


def test_selection_retry_loader_is_disabled_for_exact_pack_rows():
    from resources.lib.router_play import _selection_retry_candidate_loader

    pack = {"title": "Show.S01", "link": "", "_season_pack": {"job_id": "nzo"}}
    assert _selection_retry_candidate_loader(pack, [pack]) is None


def test_resolve_rotates_only_after_terminal_dead_candidate():
    from resources.lib import resolver
    from resources.lib.dead_candidates import DeadCandidates

    primary = "http://indexer/primary"
    alternate = {"title": "Alternate.Release", "link": "http://indexer/alternate"}
    retry_loader = MagicMock(return_value=[alternate])
    effects = resolver._ResolveSideEffects(
        {"title": "Primary.Release", "_retry_candidate_loader": retry_loader},
        [],
        None,
        primary,
        DeadCandidates(),
    )
    first_dialog = MagicMock()
    calls = []

    def submit(url, title, *_args, **_kwargs):
        calls.append((url, title))
        if url == primary:
            effects._dead.add(nzb_url=url, nzo_id="failed-primary")
            return None, None, first_dialog
        return "http://webdav/alternate.mkv", {}, MagicMock()

    with patch(
        "resources.lib.resolver._picker_completed_stream", return_value=None
    ), patch(
        "resources.lib.resolver._resolve_submit_and_poll", side_effect=submit
    ), patch(
        "resources.lib.resolver._stop_fallback_submit_worker"
    ) as stop_worker:
        result = resolver._resolve_acquire_stream(
            primary,
            "Primary.Release",
            {"title": "Primary.Release", "_retry_candidate_loader": retry_loader},
            set(),
            effects,
        )

    assert result[0] == "http://webdav/alternate.mkv"
    assert calls == [
        (primary, "Primary.Release"),
        (alternate["link"], alternate["title"]),
    ]
    retry_loader.assert_called_once_with()
    first_dialog.close.assert_called_once_with()
    stop_worker.assert_not_called()
    assert effects.playback_title == alternate["title"]


def test_resolve_does_not_rotate_transient_candidate_failure():
    from resources.lib import resolver
    from resources.lib.dead_candidates import DeadCandidates

    retry_loader = MagicMock(
        return_value=[{"title": "Alternate", "link": "http://indexer/alternate"}]
    )
    effects = resolver._ResolveSideEffects(
        {"title": "Primary", "_retry_candidate_loader": retry_loader},
        [],
        None,
        "http://indexer/primary",
        DeadCandidates(),
    )
    with patch(
        "resources.lib.resolver._picker_completed_stream", return_value=None
    ), patch(
        "resources.lib.resolver._resolve_submit_and_poll",
        return_value=(None, None, None),
    ) as submit:
        result = resolver._resolve_acquire_stream(
            "http://indexer/primary",
            "Primary",
            {"title": "Primary", "_retry_candidate_loader": retry_loader},
            set(),
            effects,
        )

    assert result == (None, None, None)
    submit.assert_called_once()
    retry_loader.assert_not_called()


def test_resolve_and_play_rotates_terminal_failure_for_script_route():
    from resources.lib import resolver
    from resources.lib.dead_candidates import DeadCandidates

    primary = "http://indexer/primary"
    alternate = {"title": "Alternate.Release", "link": "http://indexer/alternate"}
    retry_loader = MagicMock(return_value=[alternate])
    params = {"title": "Primary.Release", "_retry_candidate_loader": retry_loader}
    effects = resolver._ResolveSideEffects(
        params, [], None, primary, DeadCandidates(), settings_getter=lambda *_args: ""
    )
    first_dialog = MagicMock()
    calls = []

    def submit(url, title, *_args, **_kwargs):
        calls.append((url, title))
        if url == primary:
            effects._dead.add(nzb_url=url)
            return None, None, first_dialog
        return "http://webdav/alternate.mkv", {}, MagicMock()

    with patch(
        "resources.lib.resolver._picker_completed_stream", return_value=None
    ), patch(
        "resources.lib.resolver._resolve_and_play_submit_and_poll",
        side_effect=submit,
    ), patch(
        "resources.lib.resolver._resolve_stage"
    ):
        result = resolver._resolve_and_play_acquire_stream(
            primary, "Primary.Release", params, lambda *_args: "", effects
        )

    assert result[0] == "http://webdav/alternate.mkv"
    assert calls == [
        (primary, "Primary.Release"),
        (alternate["link"], alternate["title"]),
    ]
    assert effects.playback_title == alternate["title"]
    first_dialog.close.assert_called_once_with()


def test_primary_candidate_params_drop_stale_hints_and_copy_alternate_metadata():
    from resources.lib.resolver_entry import _params_for_primary_candidate

    params = {
        "title": "Primary",
        "nzburl": "http://indexer/primary",
        "_completed_job": {"nzo_id": "stale"},
        "_completed_job_lookup_done": True,
        "_selected_indexer": "old",
        "_download_pubdate": "old-date",
        "_download_size": "10",
        "_season_pack": {"job_id": "pack"},
    }
    result = _params_for_primary_candidate(
        params,
        {
            "title": "Alternate",
            "link": "http://indexer/alternate",
            "indexer": "new",
            "pubdate": "new-date",
            "size": "20",
        },
    )

    assert result["nzburl"] == "http://indexer/alternate"
    assert result["title"] == "Alternate"
    assert result["_selected_indexer"] == "new"
    assert result["_download_pubdate"] == "new-date"
    assert result["_download_size"] == "20"
    assert "_completed_job" not in result
    assert "_completed_job_lookup_done" not in result
    assert "_season_pack" not in result


def test_terminal_submit_rejection_marks_url_dead_for_rotation():
    from resources.lib import resolver
    from resources.lib.dead_candidates import DeadCandidates

    dead = DeadCandidates()
    with patch(
        "resources.lib.resolver._submit_nzb_with_ui_pump",
        return_value=(None, {"status": 500, "message": "missing articles"}),
    ), patch("resources.lib.resolver.xbmcgui.Dialog"):
        result = resolver._submit_nzb_with_retries(
            "http://indexer/dead",
            "Dead.Release",
            MagicMock(),
            MagicMock(),
            dead=dead,
        )

    assert result is None
    assert dead.has_url("http://indexer/dead")
