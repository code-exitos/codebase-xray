# codebase-xray

A Claude Code plugin with the `codebase-xray` skill, extracted from
[code-exitos/athanor-plugin#9](https://github.com/code-exitos/athanor-plugin/pull/9)
(commit `df9bb60`, 2026-08-06), where it shipped as `run-codebase-xray`.

It is an optional deep-dive of the brownfield Assay. It builds a dependency graph of the
codebase, walks it from the real entry points, and produces a class diagram, a
stakeholder-facing I/O map and an information-lifecycle diagram, each annotated
active / dormant / unknown / orphaned, plus a reachability brief.

How "safe to drop" is earned:

1. **Computed reachability.** `scripts/xray.py reach` classifies every graph node from the
   entry points. Possible targets of unresolved dynamic calls are `unknown`, never `dormant`.
2. **Cited claims.** Every agent finding carries a `file:line`; `xray.py cite` checks each one exists.
3. **Adversarial verification.** Each dormant drop candidate must survive two agents trying to
   prove it is still used (static references; outside callers and runtime). Otherwise it is Contested.

## Layout

```
.claude-plugin/
  plugin.json
  marketplace.json
skills/codebase-xray/SKILL.md
scripts/xray.py                                        reach | sql | cite | brief (stdlib only)
resources/templates/brownfield/reachability-brief.md
tests/test_xray.py
```

## Install

```
/plugin marketplace add code-exitos/codebase-xray
/plugin install codebase-xray@codebase-xray
```

## Tests

```
python3 -m unittest discover -s tests
```

## Credits

The graph-first approach (stack tooling before scripts, entry points from deployment config,
dispatch edges, the dynamic-call suppression rule) and the `graph.json` shape are adapted from
Anthropic's [code-modernization](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-modernization)
plugin (Apache 2.0). No code from it is included.
