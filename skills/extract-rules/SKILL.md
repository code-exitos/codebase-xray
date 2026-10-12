---
name: extract-rules
description: This skill should be used after codebase-xray has mapped a brownfield codebase, when the user asks to "extract the business rules", "pull the rules out of the plumbing", "untangle the business logic", "what does this code actually decide", or before a rewrite needs a behavior contract — mining calculations, validations, lifecycle and policy rules into cited Given/When/Then rule cards, each refereed against its source line, with every P0 rule confirmed by a two-judge panel, in context/brownfield/rules/.
---

# Extract Business Rules

The "Untangle" step. `codebase-xray` tells you what is alive; this skill tells you what the
living code **decides** — the rates, thresholds, eligibility checks, status lifecycles and
policies a replacement must keep — separated from the plumbing that happens to carry them.

The mining workflow, its agents and its renderer are adapted from the `code-modernization`
plugin in `anthropics/claude-plugins-official` (Apache 2.0; see `LICENSES/` and `NOTICE`).
What this skill adds is the shard list: it comes from the codebase-xray graph, so extraction
covers the same modules the X-ray mapped, and you can restrict it to live code.

## Prerequisites

- `context/brownfield/xray/graph.json` and `reachability.json` from `codebase-xray` Phase 1.
  Without them, run `codebase-xray` first; this skill doesn't build its own graph.
- Scripts: `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/xray.py"` and
  `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/render_rules.py"`.
- The `Workflow` tool. Workflow: `${CLAUDE_PLUGIN_ROOT}/workflows/extract-rules.js`.

All output goes in `context/brownfield/rules/`. Citations are relative to the project root.

## 1. Build shards

By default mine only code the graph says is reachable or might be (`active,unknown`): rules
in dormant code are not rules the business still runs on. Say so to the human, and offer
`--status active,unknown,dormant` if they want the dormant code mined too (for example, to
check whether a dropped module held a rule that exists nowhere else).

```bash
mkdir -p context/brownfield/rules
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/xray.py" shards context/brownfield/xray/graph.json \
  --reachability context/brownfield/xray/reachability.json --status active,unknown \
  --out context/brownfield/rules/modules.json
```

Each graph domain becomes a shard; a domain with more than 25 files is split by folder.
Business logic that lives in SQL (stored procedures, triggers) is not a graph leaf: if the
X-ray's `sql-objects.json` or the module scans show rules living there, add a shard by hand
for the relevant `.sql` files (`{"name": "SQL procedures", "files": ["database/Schema.sql"]}`),
and tell the human which file it is. A single very large `.sql` file is better split into
excerpt files first, so one extractor isn't asked to read 18,000 lines.

## 2. Estimate and launch

Estimate: 10–15 agents per shard, about 16k tokens each, about 8 agents finishing per minute.
For calibration, a 30,000-line estate in 44 shards used roughly 470–650 agents and 50–80
minutes. **With more than 12 shards, ask with AskUserQuestion before launching**, offering
"Run all N shards", "Only a slice (name the shards)" and "Cancel". With 12 or fewer, say the
count and estimate and launch.

```
Workflow({
  name: "codebase-xray:extract-rules-mine",   // or scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/extract-rules.js"
  args: {
    system: "<plain system name, letters/digits/-/_>",
    sourceDir: ".",
    modules: <contents of context/brownfield/rules/modules.json>
  }
})
```

Pass `args` as real JSON values, not a string. Record the run ID. If the run **stops**,
re-invoke with identical args plus `resumeFromRunId`. If it **completes with failures**, do
not resume: pass the returned `rerunModules` as `modules` in a follow-up run and merge.

## 3. Render and check

The workflow's agents are read-only; you write the files.

1. Save the returned object as `context/brownfield/rules/rules_result.json`.
2. Render, then check citations (the cite step reads `file`/`line` pairs; rule cards carry a
   `source` string, so the renderer's citation split is the check here — spot-check five rule
   cards against the code yourself and say what you found):

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/render_rules.py" <system> --out-dir context/brownfield/rules
```

That writes `BUSINESS_RULES.md` (summary table, `### RULE-NNN:` cards by category, rules needing
SME confirmation, instruction-shaped content, coverage gaps) and `DATA_OBJECTS.md`.

## 4. Report and hand off

Report: total rules by category and priority, how many P0, how many need an SME, how many
candidates the referees rejected (that number is what verification bought — give 2–3 examples),
how many were folded together as duplicates, and any coverage gaps.

Hand-off:
- **SME questions** go into the knowledge-capture list alongside the X-ray's questions — they
  are the "get it out of his head" material. Each P0 rule below High confidence is Blocking.
- **Suspected defects** (legacy behavior that looks wrong) are their own list: a rewrite must
  decide on purpose whether to keep the bug.
- **P0 rules** are the behavior contract: the tests that prove a migration is equivalent are
  written against them.

## Output

```
context/brownfield/rules/
  modules.json          Shards (from xray.py shards, plus any hand-added SQL shards)
  rules_result.json     Workflow result
  BUSINESS_RULES.md     Rule cards, Status: Draft
  DATA_OBJECTS.md       Core records and the rules that use them
```
