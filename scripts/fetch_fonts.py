"""T157g — vendor the reference typography locally (owner-run, one time).

The index36 reference uses IBM Plex Sans (body) and Rubik (headings), both
SIL OFL licensed. KUBERA never loads fonts from a CDN at runtime (public
money app), so this script downloads the woff2 files ONCE into
apps/web/fonts/ and the app serves them itself from /fonts/*. Until it runs,
the UI falls back to the system stack — everything works, just not
pixel-identical type.

Usage (owner machine, any venv with httpx):
    python scripts/fetch_fonts.py
"""

import re
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = REPO_ROOT / "apps" / "web" / "fonts"

# css2 API returns woff2 URLs when asked with a modern UA
CSS_URL = ("https://fonts.googleapis.com/css2"
           "?family=IBM+Plex+Sans:wght@400;500;600;700"
           "&family=Rubik:wght@500;600;700&display=swap")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

FACE_RE = re.compile(
    r"font-family:\s*'([^']+)';\s*font-style:\s*normal;\s*font-weight:\s*(\d+);"
    r".*?src:\s*url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)",
    re.S)

SLUG = {"IBM Plex Sans": "ibm-plex-sans", "Rubik": "rubik"}


def main() -> int:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, timeout=30.0,
                      follow_redirects=True) as c:
        css = c.get(CSS_URL)
        css.raise_for_status()
        got = 0
        for fam, weight, url in FACE_RE.findall(css.text):
            if fam not in SLUG:
                continue
            # css2 lists one url per unicode-range block; keep the LAST
            # (latin) occurrence per family+weight by overwriting the file
            name = f"{SLUG[fam]}-{weight}.woff2"
            data = c.get(url)
            data.raise_for_status()
            (FONT_DIR / name).write_bytes(data.content)
            got += 1
            print(f"  {name}  ({len(data.content):,} bytes)")
        if got == 0:
            print("NO FONTS PARSED — Google may have changed the CSS shape; "
                  "open the URL in a browser and report to ISSUES.md")
            return 1
    print(f"done — {got} file writes into {FONT_DIR}")
    print("licenses: SIL OFL 1.1 (IBM Plex Sans: IBM; Rubik: Hubert & Fischer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
