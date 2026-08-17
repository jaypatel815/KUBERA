"""T016 — get a Schwab refresh token (D026). Run this on YOUR machine, once a week.

    python scripts/schwab_auth.py            # print the token
    python scripts/schwab_auth.py --write    # also update .env in place

WHAT HAPPENS, so nothing surprises you:

  1. This prints an authorisation URL and opens it in your browser.
  2. You log in to Schwab and approve the app. Read-only is all KUBERA asks for.
  3. Schwab redirects your browser to your registered callback URL with a `code`
     in the query string.
  4. **YOUR BROWSER WILL SHOW AN ERROR PAGE. THAT IS THE EXPECTED OUTCOME.**
     Schwab requires an HTTPS callback, and there is no server listening on
     https://127.0.0.1 — so you get "can't establish a secure connection" or
     similar. The redirect still happened; the code is sitting in the address
     bar. Copy the WHOLE URL and paste it below.
  5. This exchanges the code for tokens and verifies the refresh token works by
     making one real read-only call before you walk away.

WHY PASTE A URL INSTEAD OF RUNNING A LOCAL SERVER: catching the redirect
automatically means running an HTTPS listener, which means generating and
trusting a self-signed certificate. That is a lot of moving parts, and every one
of them fails differently on Windows. Copying one URL is uglier and works.

THE CODE EXPIRES IN ABOUT 30 SECONDS. If the exchange fails with "invalid
authorization code", you were simply too slow — run it again and paste faster.

The refresh token lasts roughly SEVEN DAYS. When KUBERA starts reporting "token
refresh failed", that is this, and it is not a bug.
"""

import argparse
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from settings import ConfigError, KuberaSettings, get_settings  # noqa: E402


def build_auth_url(app_key: str, callback: str, settings: KuberaSettings | None = None) -> str:
    """The URL that starts the browser flow. `readonly` is not a Schwab scope —
    read-only is enforced by KUBERA's client having no order methods (D026)."""
    s = settings or get_settings()
    auth_url = s.schwab_auth_url
    return f"{auth_url}?client_id={quote(app_key, safe='')}&redirect_uri={quote(callback, safe='')}"


def extract_code(pasted: str) -> str:
    """Pull `code` out of the pasted redirect URL.

    Schwab appends a session suffix and URL-encodes the value, so naive string
    splitting mangles it. parse_qs decodes properly; the trailing '@' that
    Schwab adds is part of the code and must be kept.
    """
    text = pasted.strip().strip('"').strip("'")
    if not text:
        raise ValueError("Nothing pasted.")
    query = urlparse(text).query
    if not query:
        raise ValueError(
            "That does not look like a redirect URL — no query string. Paste the "
            "ENTIRE address from the browser bar, starting with https://"
        )
    code = parse_qs(query).get("code", [""])[0]
    if not code:
        params = ", ".join(sorted(parse_qs(query))) or "(none)"
        raise ValueError(f"No `code` parameter in that URL. Parameters found: {params}")
    return code


def exchange(
    app_key: str,
    app_secret: str,
    callback: str,
    code: str,
    transport: httpx.BaseTransport | None = None,
    settings: KuberaSettings | None = None,
) -> dict:
    s = settings or get_settings()
    token_url = s.schwab_token_url
    with httpx.Client(transport=transport, timeout=30.0) as client:
        resp = client.post(
            token_url,
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": callback},
            auth=(app_key, app_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code >= 400:
        body = resp.text[:300]
        hint = ""
        if "invalid" in body.lower() and "code" in body.lower():
            hint = ("\n  Most likely cause: the code expired — it is good for about 30 "
                    "seconds. Run this again and paste more quickly.")
        elif resp.status_code == 401:
            hint = ("\n  Most likely cause: SCHWAB_APP_KEY / SCHWAB_APP_SECRET do not match "
                    "the app, or the app is not yet in 'Ready For Use' at developer.schwab.com.")
        elif "redirect" in body.lower():
            hint = ("\n  Most likely cause: the callback URL here does not EXACTLY match the "
                    "one registered on the app — trailing slashes and http/https both count.")
        raise SystemExit(f"Token exchange failed (HTTP {resp.status_code}):\n  {body}{hint}")
    return resp.json()


def write_env(refresh_token: str) -> Path:
    """Update SCHWAB_REFRESH_TOKEN in .env, preserving everything else."""
    env = ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith("SCHWAB_REFRESH_TOKEN="):
            lines[i] = f"SCHWAB_REFRESH_TOKEN={refresh_token}"
            replaced = True
            break
    if not replaced:
        lines.append(f"SCHWAB_REFRESH_TOKEN={refresh_token}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description="Obtain a Schwab refresh token (read-only).")
    ap.add_argument("--write", action="store_true", help="update .env in place")
    ap.add_argument("--no-browser", action="store_true", help="print the URL, do not open it")
    args = ap.parse_args()

    s = get_settings()
    if not s.schwab_app_key or not s.schwab_app_secret:
        # A bare "must be in .env first" is useless when they ARE in .env and
        # something else is wrong. Say which file was read and what was found in
        # it, so the next question is answerable instead of a guessing game.
        env_path = Path(KuberaSettings.model_config.get("env_file", ROOT / ".env"))
        print("SCHWAB_APP_KEY and SCHWAB_APP_SECRET are not reaching the code.\n")
        print(f"  reading   {env_path}")
        print(f"  exists    {env_path.exists()}")
        print(f"  app key   {'set' if s.schwab_app_key else 'MISSING'}")
        print(f"  app secret{' set' if s.schwab_app_secret else ' MISSING'}")
        print("\nBoth come from your app at https://developer.schwab.com.")
        print("If they ARE in that file, run this to find out why they are not")
        print("being read (prints names and lengths, never values):\n")
        print("  python scripts/env_check.py SCHWAB")
        return 2
    app_key = s.schwab_app_key
    app_secret = s.schwab_app_secret.get_secret_value()
    callback = s.schwab_callback_url

    url = build_auth_url(app_key, callback)
    print("BEFORE YOU START — two things that cause 99% of failures here:")
    print("  1. Your app's status at developer.schwab.com must read exactly")
    print("     'Ready For Use'. Two statuses are NOT ready: 'Approved - Pending'")
    print("     (first approval) and 'Modification Pending' (you edited the app).")
    print("     ANY edit — including the callback URL — restarts the review, and")
    print("     editing again while pending restarts it AGAIN. Change nothing.")
    print("  2. The callback below must match the app's registered one BYTE FOR")
    print("     BYTE — scheme, case, port, trailing slash all count.\n")
    print("If you log in, accept the terms, and then get 'We are unable to")
    print("complete your request' while receiving an 'access preferences")
    print("updated' email, that is symptom #1: the account linked, the app")
    print("could not. Nothing on this side will fix it; wait for Ready For Use.\n")
    print("STEP 1 — approve KUBERA in the browser")
    print(f"  callback being sent: {callback}   <-- must match the app EXACTLY")
    print(f"  {url}\n")
    if not args.no_browser:
        webbrowser.open(url)

    print("STEP 2 — your browser will land on an ERROR PAGE. That is expected:")
    print("  Schwab requires an https callback and nothing is listening there.")
    print("  The code is in the address bar anyway.\n")
    print("STEP 3 — paste the ENTIRE redirected URL here (you have ~30 seconds):")
    try:
        pasted = input("  > ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1

    try:
        code = extract_code(pasted)
    except ValueError as e:
        print(f"\n{e}")
        return 2

    payload = exchange(app_key, app_secret, callback, code)
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        print(f"No refresh_token in the response. Keys returned: {sorted(payload)}")
        return 2

    # Prove it works before you walk away, rather than discovering it tomorrow.
    print("\nVerifying the token with one read-only call...")
    try:
        from data.schwab import SchwabClient  # noqa: PLC0415

        probe = get_settings().model_copy(update={"schwab_refresh_token": refresh_token})
        with SchwabClient(probe) as c:
            accounts = c.list_accounts()
        print(f"  OK — {len(accounts)} account(s): "
              f"{', '.join(a.number_masked for a in accounts)}")
    except Exception as e:                      # noqa: BLE001 — report, never crash the flow
        print(f"  Token obtained, but the verification call failed: {e}")
        print("  The token below is probably still good; the failure may be app scopes.")

    if args.write:
        path = write_env(refresh_token)
        print(f"\nWritten to {path} (SCHWAB_REFRESH_TOKEN updated).")
    else:
        print("\nAdd this line to .env (or re-run with --write):\n")
        print(f"SCHWAB_REFRESH_TOKEN={refresh_token}")

    print("\nThis expires in about 7 days. When KUBERA says 'token refresh failed',")
    print("run this again — that is the cause, not a bug.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as e:
        print(str(e))
        sys.exit(2)
