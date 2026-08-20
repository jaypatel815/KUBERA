"""T087b — the shared toast helper: escaping pinned, failures swallowed."""

import subprocess

import notify
from notify import notify_windows, ps_script


def test_apostrophes_are_escaped_the_original_bug():
    """The promoted-from-health_check quoting bug: an apostrophe in the
    message must become a doubled quote, not a broken PowerShell script."""
    s = ps_script("KUBERA monitor: 1 alert(s)",
                  "SPY [invalidation_hit] the plan you ratified says the "
                  "thesis is dead; today's tape disagrees")
    assert "today''s" in s                 # escaped
    assert "today's tape" not in s         # the raw form is GONE
    assert s.count("ShowBalloonTip") == 1


def test_newlines_flatten_and_length_caps():
    s = ps_script("t", "line1\nline2\n" + "x" * 500)
    assert "\n" not in s.split("ShowBalloonTip")[1]
    # message body capped at 200 chars BEFORE quoting
    body = s.split(",'")[2].split("','Warning'")[0]
    assert len(body) <= 210                # cap + a few doubled quotes


def test_notify_never_raises(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("no powershell here")
    monkeypatch.setattr(subprocess, "run", boom)
    notify_windows("t", "m")               # swallowed, by contract

    def hang(*a, **k):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=15)
    monkeypatch.setattr(subprocess, "run", hang)
    notify_windows("t", "m")               # also swallowed


def test_call_shape(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: calls.append((a, k)))
    notify.notify_windows("Title", "Message")
    (argv,), kw = calls[0]
    assert argv[:3] == ["powershell", "-NoProfile", "-Command"]
    assert kw["timeout"] == 15 and kw["check"] is False
