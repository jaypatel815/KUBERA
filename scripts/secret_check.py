"""T130 — public-repo secrets hygiene, mechanized (Phase 8 "security pass").

This repo is PUBLIC. Three checks, each of which has already earned its
place by catching a real defect somewhere in this project's history:

1. TRACKED-FILE SCAN — every `git ls-files` text file is scanned for
   key-shaped strings (AWS, GitHub, Slack, OpenAI-style, private-key PEM
   blocks, Alpaca-shaped IDs) and for suspicious `key/secret/token =
   "<long literal>"` assignments. Placeholders ("your-...", "example",
   "changeme") are recognized and skipped — .env.example must be able to
   document a variable without tripping the alarm.
2. EXAMPLE PARITY (one-way, both directions of the ONE-way):
   - every variable documented in .env.example must resolve to a real
     settings field or alias — dead documentation misleads the owner;
   - every CREDENTIAL-class settings field (SecretStr) must be documented
     in .env.example — T114 found FMP_API_KEY missing entirely, by hand;
     this makes that find mechanical.
3. SECRETSTR FLOOR — any settings field whose name contains "secret",
   ends in "_api_key", or ends in "_token" must be typed SecretStr, so it
   can never leak through repr/logs. (IDs like alpaca_api_key_id and
   schwab_app_key are identifiers, not secrets, and stay plain str by
   design — the floor is deliberately narrower than the practice.)

Exit codes: 0 clean, 1 findings (each named with file:line), 2 cannot run.
Values are NEVER printed — findings show file, line number, and pattern
name only. A secrets checker that echoes the secret is the leak.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

# --- 1. tracked-file scan ---------------------------------------------------

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9_\-]{32,}\b")),
    ("private-key-pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("alpaca-shaped-id", re.compile(r"\b[PA]K[A-Z0-9]{18}\b")),
    ("credential-assignment", re.compile(
        r"(?i)(api_key|apikey|secret|token|password)\s*[=:]\s*"
        r"[\"']([A-Za-z0-9+/=_\-]{16,})[\"']")),
]

PLACEHOLDER = re.compile(r"(?i)your|example|changeme|placeholder|dummy|"
                         r"redacted|xxxx|<[^>]+>")

SKIP_SUFFIXES = {".png", ".jpg", ".ico", ".onnx", ".bin", ".sqlite3",
                 ".pdf", ".woff", ".woff2", ".zip"}


def scan_content(path: str, text: str) -> list[str]:
    """Findings for one file — file:line + pattern NAME, never the value."""
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pat in PATTERNS:
            m = pat.search(line)
            if m is None:
                continue
            # a placeholder VALUE is documentation, not a leak
            probe = m.group(2) if name == "credential-assignment" else line
            if PLACEHOLDER.search(probe):
                continue
            findings.append(f"{path}:{lineno}: matches {name}")
    return findings


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True,
        text=True, encoding="utf-8", errors="replace", check=True)
    return [f for f in out.stdout.splitlines()
            if Path(f).suffix.lower() not in SKIP_SUFFIXES]


def scan_repo() -> list[str]:
    findings: list[str] = []
    for rel in tracked_files():
        p = REPO_ROOT / rel
        if rel == "scripts/secret_check.py":
            continue  # this file NAMES the patterns it hunts
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        findings += scan_content(rel, text)
    return findings


# --- 2 + 3. settings introspection ------------------------------------------

def settings_field_specs() -> list[tuple[str, list[str], bool]]:
    """(field_name, [env names incl. aliases], is_secretstr) per field."""
    from settings import KuberaSettings

    specs = []
    for name, field in KuberaSettings.model_fields.items():
        env_names = {name.upper()}
        alias = getattr(field, "validation_alias", None)
        if alias is not None:
            for choice in getattr(alias, "choices", []) or []:
                env_names.add(str(choice).upper())
        is_secret = "SecretStr" in str(field.annotation)
        specs.append((name, sorted(env_names), is_secret))
    return specs


_VAR_LINE = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)=")


def example_vars(example_text: str) -> set[str]:
    """Vars the example documents — including the file's own convention of
    COMMENTED optional vars ('# OPENAI_API_KEY=' documents a real knob)."""
    out = set()
    for line in example_text.splitlines():
        m = _VAR_LINE.match(line.strip())
        if m:
            out.add(m.group(1))
    return out


_RUNTIME_READ = re.compile(
    r"""os\.(?:environ\.get|getenv)\(\s*["']([A-Z][A-Z0-9_]*)["']""")


def runtime_env_vars(backend_dir: Path | None = None) -> set[str]:
    """Vars the app reads at RUNTIME through os.environ (I039: the voice
    knobs — KUBERA_VOICE and friends — are deliberately settings-free so
    they can change without a restart). Documenting one of these is not
    dead documentation; the parity check must know they exist."""
    d = backend_dir or (REPO_ROOT / "backend")
    out: set[str] = set()
    for f in d.rglob("*.py"):
        if "__pycache__" in f.parts or "tests" in f.parts:
            continue
        out.update(_RUNTIME_READ.findall(f.read_text(encoding="utf-8")))
    return out


def check_parity(specs, documented: set[str],
                 runtime_read: set[str] | None = None) -> list[str]:
    findings = []
    known = {env for _, envs, _ in specs for env in envs}
    known |= runtime_read or set()
    for var in sorted(documented - known):
        findings.append(
            f".env.example documents {var} but nothing reads it (neither "
            "settings.py nor a runtime os.environ read in backend/) "
            "— dead documentation misleads the owner")
    for name, envs, is_secret in specs:
        if is_secret and not (set(envs) & documented):
            findings.append(
                f"credential field '{name}' is not documented in "
                ".env.example — the owner cannot configure what he cannot "
                "see (the FMP_API_KEY class of bug, T114)")
    return findings


def check_secretstr_floor(specs) -> list[str]:
    findings = []
    for name, _envs, is_secret in specs:
        must = ("secret" in name or name.endswith("_api_key")
                or name.endswith("_token"))
        if must and not is_secret:
            findings.append(
                f"settings field '{name}' looks like a credential but is "
                "not SecretStr — it can leak via repr/logs")
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Public-repo secrets hygiene (T130).")
    ap.add_argument("--example", type=Path,
                    default=REPO_ROOT / ".env.example")
    args = ap.parse_args(argv)

    try:
        findings = scan_repo()
        specs = settings_field_specs()
    except Exception as e:  # noqa: BLE001 — cannot run = named exit 2
        print(f"CANNOT RUN: {type(e).__name__}: {e}")
        return 2
    if not args.example.exists():
        print(f"CANNOT RUN: no {args.example}")
        return 2
    documented = example_vars(args.example.read_text(encoding="utf-8"))
    findings += check_parity(specs, documented, runtime_env_vars())
    findings += check_secretstr_floor(specs)

    if not findings:
        print(f"SECRETS: CLEAN — {len(tracked_files())} tracked files "
              f"scanned, {len(specs)} settings fields checked, "
              f"{len(documented)} documented vars all real")
        return 0
    for f in findings:
        print(f"FINDING: {f}")
    print(f"SECRETS: {len(findings)} finding(s) — values never printed; "
          "open the named lines yourself")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
