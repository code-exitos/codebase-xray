# Severity Classification

All reviewer agents (security, testing-observability, performance-scalability, simplicity-maintainability, and quick-reviewer for small diffs) and third-party reviewer findings (CodeRabbit, Cursor Bugbot) use this classification. The two passes gate at different depths — see the Gate Summary below.

| Severity | Definition | Gate behavior | Roughly equivalent to |
|---|---|---|---|
| **Critical** | Exploitable security issue, data loss risk, a bug that breaks a stated acceptance criterion, or test-contract tampering (a weakened/removed pre-existing assertion — see `testing-observability-reviewer.md`). This list is illustrative, not exhaustive — a finding this severe in kind, even if not named here, is still Critical. | Blocks merge; must be resolved | SEV0/SEV1, P0 |
| **High** | Meaningful risk to correctness, security posture, or performance at realistic scale; not yet exploitable/broken but close | Blocks merge; must be resolved | SEV2, P1 |
| **Medium** | Real issue, but contained/non-urgent — e.g. missing test for an edge case, minor inefficiency | Internal pass: should be resolved; may be explicitly deferred with a logged reason and follow-up issue, at TD/engineer discretion. Third-party pass: must be resolved | SEV3, P2 |
| **Low / Nit** | Style, naming, minor readability preference | Does not block merge — may remain open at human-approval time | SEV4, P3 |

**Excessive/redundant comments** (per `simplicity-maintainability-checklist.md`) are a **Low/Nit** (issue #157). They are always reported, with the count, and fixed when cheap, but on their own they never restart a review loop.

The "roughly equivalent to" column exists for translating with people used to incident-response
vocabulary (SEV0–SEV4, P0–P3 — common at PagerDuty/Opsgenie-style shops) — it's an orientation
aid, not a second scale to maintain. **Severity and priority are different axes**, per the
Google SRE Workbook's distinction: severity is the objective impact of a finding; priority
(the `P1`/`P2`/`P3` field on a User Story or Task issue) is the order work gets picked up in,
which factors in severity plus effort, dependencies, and timing. A **Low/Nit** code-review
finding and a **P1** user story are not in tension — they're answering different questions.

**A third-party reviewer's own labels don't map onto this scale.** External tools use their own vocabulary — "potential issue", "refactor suggestion", "nitpick", "trivial" — and they routinely understate: a real authorization gap filed as a refactor suggestion is **High**. Re-classify every external finding on this scale, on its merits, not on the vendor's label.

## Gate Summary

Two passes, two depths (Core Rule #7):

- **Athanor's pass, pre-PR** (`run-code-review`: four pillars, or `quick-reviewer` alone on a small diff) — **Critical and High** block opening the PR. Medium should be fixed, and may be deferred with a logged reason and a follow-up issue.
- **The third-party pass, post-PR** (`resolve-external-review`) — resolve until only **nits** remain, **Medium included**. This is the last gate before a human is asked to approve, so a Medium doesn't get deferred a second time here; in practice it's often the same Medium the internal pass set aside.

Only nit-level findings may remain open at the point of human approval.

Each pass runs **at most two rounds** (Core Rule #8). If findings above nit level are still open after the second round, stop and ask the human how to go on — never open or merge with a Critical or High open on your own.

A finding **refuted in-thread with a stated reason** — typically because the fix would introduce complexity the simplicity pillar would flag — counts as resolved for this gate. One silently skipped does not.
