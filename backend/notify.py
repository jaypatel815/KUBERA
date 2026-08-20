"""Windows toast notifications (T087b) — one hardened implementation.

Grew out of scripts/health_check.py's inline helper, promoted here when the
monitor needed the same thing — two copies of subprocess-into-PowerShell is
two places to get quoting wrong. And the original HAD a quoting bug waiting:
it interpolated raw text into single-quoted PowerShell, so any message
containing an apostrophe ("today's tape") would have broken the script.
health_check's fixed messages never tripped it; the monitor's alert details
(which quote exit-plan reasons) absolutely would have.

Best-effort by contract: a notification is never worth crashing over — no
PowerShell (non-Windows, stripped PATH), a hung shell, or any other failure
is swallowed after a bounded wait. The CALLER's exit code carries the truth;
the toast is just a tap on the shoulder.
"""

from __future__ import annotations

import subprocess

_MAX_LEN = 200          # balloon tips truncate anyway; keep the script bounded


def _ps_quote(text: str, limit: int = _MAX_LEN) -> str:
    """PowerShell single-quoted literal escaping: double the quotes.
    Newlines become spaces (balloon tips render them as boxes)."""
    flat = " ".join(str(text).split())[:limit]
    return flat.replace("'", "''")


def ps_script(title: str, message: str) -> str:
    """The PowerShell balloon-tip script (pure; the tests pin the escaping)."""
    return (
        "[reflection.assembly]::loadwithpartialname('System.Windows.Forms')|Out-Null;"
        "$n=New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon=[System.Drawing.SystemIcons]::Warning;$n.Visible=$true;"
        f"$n.ShowBalloonTip(10000,'{_ps_quote(title, 60)}',"
        f"'{_ps_quote(message)}','Warning')"
    )


def notify_windows(title: str, message: str) -> None:
    """Best-effort toast; silently a no-op anywhere it can't work."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script(title, message)],
            capture_output=True, timeout=15, check=False,
        )
    except Exception:  # noqa: BLE001 — notification is never worth crashing over
        pass
