# Vendored fonts (T157g)

IBM Plex Sans + Rubik woff2 files land here after the owner runs, once:

    python scripts/fetch_fonts.py

Both are SIL OFL 1.1 licensed. Files here are gitignored-by-size policy?
NO - they are committed once fetched so the app has no runtime CDN
dependency. Until then the UI falls back to the system font stack.
