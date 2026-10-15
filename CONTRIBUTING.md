# Contributing to codebase-xray

Thanks for helping. Bug reports, fixes, and improvements to the skills are all welcome.

By taking part you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Security problems
go through [SECURITY.md](SECURITY.md), not public issues.

## Reporting a bug or asking for a feature

Open an issue. For a bug, include:

- which skill or script (`codebase-xray`, `extract-rules`, `security-sweep`, `xray.py <command>`)
- the stack of the codebase you ran it on (language, framework, rough size)
- what you expected and what happened, with the error or the wrong output

If the bug comes from a specific codebase, a small sample that reproduces it helps most. Do not
paste proprietary code.

## Working on the plugin

Clone the repo and load it straight into Claude Code from the clone:

```
git clone https://github.com/code-exitos/codebase-xray.git
claude --plugin-dir ./codebase-xray
```

Run the tests before you push:

```
python3 -m unittest discover -s tests
```

A few rules for the code:

- **`scripts/` stays standard library only.** People run it on locked-down machines against
  legacy estates; no `pip install`.
- **Verdicts come from scripts, not models.** Reachability, SQL status and citation checks live
  in `xray.py` so a result can be re-checked. Keep it that way, and add a test in
  `tests/test_xray.py` for any change to them.
- **Every finding is cited.** A skill or agent change must still produce a `file:line` for each
  claim.
- **Bump `version` in `.claude-plugin/plugin.json`** when a change affects people who installed
  the plugin.

## Files copied from code-modernization

Some files come from Anthropic's code-modernization plugin and stay under its Apache 2.0 terms;
`NOTICE` lists them. If you change one:

- keep its copyright header, and update the `MODIFIED by CODE Éxitos` line to describe the change
- if you copy in another file from that plugin, add the same header and list it in `NOTICE`

## Pull requests

1. Branch from `main`.
2. Keep each PR to one change, and update `README.md` if the change affects how people use the
   plugin.
3. Write commit messages in the style already in the log: `feat:`, `fix:`, `refactor:`,
   `chore:`, with an optional scope, as in `fix(xray.py sql): ...`.
4. Make sure the tests pass, then open the PR and say what changed and why.

## License

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the same as the rest of the project.
