# codebase-xray

The `run-codebase-xray` skill, extracted from
[code-exitos/athanor-plugin#9](https://github.com/code-exitos/athanor-plugin/pull/9)
(commit `df9bb60`, 2026-08-06) as a standalone skill.

It is an optional deep-dive of the brownfield Assay. It produces a class diagram,
a stakeholder-facing I/O map and an information-lifecycle diagram, each annotated
active / dormant / orphaned, plus a reachability brief.

## Files

- `SKILL.md`: the skill.
- `reachability-brief.md`: the brief template the skill fills in.

`SKILL.md` references the template at
`${CLAUDE_PLUGIN_ROOT}/resources/templates/brownfield/reachability-brief.md`;
adjust that path when using the skill outside the Athanor plugin.
