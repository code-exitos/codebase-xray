# codebase-xray

A Claude Code plugin with the `codebase-xray` skill, extracted from
[code-exitos/athanor-plugin#9](https://github.com/code-exitos/athanor-plugin/pull/9)
(commit `df9bb60`, 2026-08-06), where it shipped as `run-codebase-xray`.

It is an optional deep-dive of the brownfield Assay. It produces a class diagram,
a stakeholder-facing I/O map and an information-lifecycle diagram, each annotated
active / dormant / orphaned, plus a reachability brief.

## Layout

```
.claude-plugin/
  plugin.json
  marketplace.json
skills/codebase-xray/SKILL.md
resources/templates/brownfield/reachability-brief.md
```

## Install

```
/plugin marketplace add code-exitos/codebase-xray
/plugin install codebase-xray@codebase-xray
```
