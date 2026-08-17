# KUBERA Selection Rule — pre-registered promotion standard

Version: v1 (2026-08-17)

This is the standard by which a strategy earns (or keeps) promotion to the
paper loop. It is PRE-REGISTERED (D029): it was written before the experiments
it will judge, every promotion run records the version that judged it, and a
change to this rule NEVER applies to results already seen — a new version takes
effect only for runs made after the change is committed. A near-miss under the
current version is a miss; the standard does not move after a result is known.

## Hard gates (enforced in code, cited here)

1. **Walk-forward consistency (T064, `backtest/stats.walk_forward`).**
   Anchored walk-forward on real history: overall return > 0 AND at least
   ceil(n/2) of n segments non-negative (default n=4). A consistency screen,
   not a promise.
2. **Promotion expiry (T064b, `backtest/ledger.is_promoted`).**
   A pass is evidence, not a lifetime badge: it expires after 180 days
   (PROMOTION_MAX_AGE_DAYS). The paper loop refuses new buys for unpromoted or
   stale pairs; sells always work.

## Required evidence at review (recorded, currently advisory)

3. **Parameter stability (T092, `scripts/sweep.py --record`).**
   The parameter neighborhood must be swept and the verdict recorded beside the
   promotion. A "curve_fit" or "reject" verdict is a red flag a reviewer must
   address in writing before relying on the promotion; hardening this into a
   refusing gate is a candidate for v2 of this rule, not a silent practice.
4. **Cost stress (T109).** Every backtest reports itself at 2x assumed costs
   beside the base run. A result that dies at 2x costs is cost-fragile and the
   review must say so.

## Comparative selection (champion semantics, D029)

When two candidates compete for the same slot — two strategies for one
(symbol, role), or a revision against the strategy it would replace:

- **Ties go to the incumbent.** The challenger must be BETTER under the gates
  above on the comparison window, not merely not-worse. "Practically identical"
  promotes the incumbent.
- **Development-period performance is never a gate.** Only out-of-sample
  segments count toward promotion. A large in-sample improvement is a reason
  for suspicion, not promotion.
- **One structural change per revision.** A challenger differing from the
  incumbent by more than one structural change is unattributable and is not
  eligible for comparison until split.

## Change control

Amend by committing a new version of this file (bump the Version line, keep a
dated changelog below). The promotion CLI refuses to run if this file is
missing or unversioned — restoring it from git is the only correct fix.

### Changelog
- v1 (2026-08-17): initial pre-registration. Codifies the already-enforced
  T064/T064b gates, records T092/T109 as required evidence, adopts
  ties-to-incumbent, dev-is-never-a-gate, and one-structural-change-per-revision
  from D029.
