# ISSUES

Known bugs and gotchas, so no agent re-diagnoses one from scratch. Format per PROJECT_SPEC.md §11.
Close entries by moving them to the bottom under "Resolved" with the fix commit.

## Open
(none)

## Resolved
- I003 — Owner's Windows-installed pre-commit hook (T008) cannot execute inside the Cowork
  Linux sandbox ("cannot run .git/hooks/pre-commit"). Sandbox commits therefore use
  `git commit --no-verify` **only after** an explicit check that `.env` is not staged
  (`git diff --cached --name-only | grep '^\.env$'` must be empty). Secret scanning still
  runs on the owner's machine and in CI (gitleaks job). Logged 2026-08-11.
- I002 — Cowork sandbox egress runs through a SOCKS proxy: httpx needs `pip install socksio`,
  and `alpaca.markets` is not on the sandbox allowlist (ProxyError 403). Consequence: live
  Alpaca integration tests always SKIP inside Cowork; they run for real on the owner's machine
  and anywhere with open egress. Not a code bug. Logged 2026-08-11.
- I001 — git inside the Claude Cowork sandbox cannot delete its own lock/temp files on the
  mounted folder ("Operation not permitted"), leaving a stale `.git/index.lock` that blocks the
  next git write. Fix (Cowork sessions only): call the `allow_cowork_file_delete` tool once,
  then `rm -f .git/*.lock` and delete `.git/objects/**/tmp_obj_*`. Windows/Antigravity/other
  agents are unaffected. Resolved 2026-08-11.
