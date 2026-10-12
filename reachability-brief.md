---
Status: Draft | Under Review | Approved
Approved By:
Approved Date:
Last Updated:
Supersedes: <link to previous version, if any>
Derived From: <run-codebase-xray output — module list and scan date>
---

# Reachability Brief

## Reachability Summary

| Category | Active | Dormant | Orphaned |
|---|---|---|---|
| Classes | | | |
| I/O Surfaces | | | |

## Load-Bearing (must survive modernization)
-

## Safe to Drop (dormant — candidate for removal, not yet confirmed with client)
- Item: <What> — Evidence it's dormant: — Confirmed with client: yes/no

## Questions for Retiring/Departing Developers
- Question: <What> — Category: Blocking | Non-blocking — Owner:

## SQL Objects Not Called From Application Code
- Object: <Name> — Type: — Tables touched: — Verified with DBA: yes/no

## SQL Objects With Unknown Call Status (Needs Verification)
*Call status could not be determined from the code alone — confirm with a DBA before treating
these as either active or safe to drop.*
- Object: <Name> — Type: — Tables touched:

## Diagrams
- Class diagram: `context/brownfield/diagrams/class-diagram.mmd`
- System I/O map: `context/brownfield/diagrams/io-map.mmd`
- Information lifecycle: `context/brownfield/diagrams/lifecycle.mmd`
