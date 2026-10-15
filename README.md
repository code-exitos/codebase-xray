# codebase-xray

A Claude Code plugin for untangling brownfield codebases. Three skills, meant to run in order:

| Skill | Story | What it produces |
|---|---|---|
| `codebase-xray` | Map, Prune, Capture | Dependency graph, reachability, three diagrams, verified safe-to-drop list, questions for the original authors |
| `extract-rules` | Untangle | Cited Given/When/Then business-rule cards from live code, refereed, P0s panel-confirmed |
| `security-sweep` | Secure | Ranked OWASP findings, Critical/High panel-checked, then fixes the human picks |

The `codebase-xray` skill was extracted from
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
skills/extract-rules/SKILL.md
skills/security-sweep/SKILL.md
agents/business-rules-extractor.md                     from code-modernization (modified)
agents/legacy-analyst.md                               from code-modernization (modified)
agents/security-reviewer.md                            adapted from Athanor for whole-code sweeps
workflows/extract-rules.js                             from code-modernization (modified)
scripts/xray.py                                        reach | sql | cite | brief | shards | security (stdlib only)
scripts/render_rules.py                                from code-modernization (modified)
resources/templates/brownfield/reachability-brief.md
resources/standards/security-checklist.md              from Athanor
resources/standards/severity-classification.md         from Athanor
LICENSE
LICENSES/Apache-2.0-code-modernization.txt
NOTICE
CODE_OF_CONDUCT.md
CONTRIBUTING.md
SECURITY.md
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Everyone taking part follows the
[Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately as described in
[SECURITY.md](SECURITY.md).

## Credits

The graph-first approach (stack tooling before scripts, entry points from deployment config,
dispatch edges, the dynamic-call suppression rule) and the `graph.json` shape are adapted from
Anthropic's [code-modernization](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-modernization)
plugin (Apache 2.0).

The `extract-rules` workflow, its two agents and `render_rules.py` are copied from that plugin
and modified; each modified file says so at the top, and `NOTICE` lists them. They stay under
the Apache License 2.0 (`LICENSES/Apache-2.0-code-modernization.txt`). This plugin is not
affiliated with or endorsed by Anthropic.

The `security-reviewer` agent and the security checklist and severity guide come from
[code-exitos/athanor-plugin](https://github.com/code-exitos/athanor-plugin).

## License

Copyright CODE Éxitos. Licensed under the [Apache License 2.0](LICENSE). See `NOTICE` for the
files that come from Anthropic's code-modernization plugin, which stay under their own Apache 2.0 terms.
