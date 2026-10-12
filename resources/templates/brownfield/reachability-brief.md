---
Status: Draft | Under Review | Approved
Approved By:
Approved Date:
Last Updated:
Supersedes: <link to previous version, if any>
Derived From: <codebase-xray — module list; how the graph was built>
---

# Reachability Brief

*Rendered by `scripts/xray.py brief` from `context/brownfield/xray/`. Reachability is computed from
the dependency graph walked from its entry points, not judged by a model.*

## Reachability Summary

| Category | Active | Dormant | Unknown | Orphaned |
|---|---|---|---|---|
| Graph nodes | | | | |
| Classes | | | | — |
| I/O surfaces | | | | — |

Entry points: <graph leaf ids>

## Load-Bearing (must survive modernization)
- **<Item>** — <why> `<file:line>`

## Safe to Drop (verified dormant — not yet confirmed with client)
*Unreachable in the graph and survived two independent agents trying to prove it is still used.*
- **<Item>** `<file:line>` — <evidence> — Confirmed with client: yes/no

## Contested (a verifier found a possible use — do not drop)
- **<Item>** `<file:line>` — <counter-evidence> `<file:line>`

## Questions for Retiring/Departing Developers
- <Question> — Blocking | Non-blocking — Owner:

## Possible Dynamic Targets (Unknown)
- `<leaf id>` — <reason and call site>

## SQL Objects Not Called From Application Code
- <Name> (<type>) `<file:line>` — referenced from SQL: — Verified with DBA: yes/no

## SQL Objects With Unknown Call Status (Needs Verification)
*Dynamic SQL is present, so no static reference does not mean unused — confirm with a DBA.*
- <Name> (<type>) `<file:line>`

## Orphaned References
- `<source>` → `<missing name>` <site>

## Citations That Failed Checking
- `<file:line>` (missing-file | bad-line | outside-root)

## Diagrams
- Class diagram: `context/brownfield/diagrams/class-diagram.mmd`
- System I/O map: `context/brownfield/diagrams/io-map.mmd`
- Information lifecycle: `context/brownfield/diagrams/lifecycle.mmd`
