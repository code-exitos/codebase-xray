## What and why

<!-- What this PR changes and the problem it solves. Link the issue if there is one. -->

## Checklist

- [ ] `python3 -m unittest discover -s tests` passes
- [ ] Changes to `xray.py` verdicts (reach, sql, cite, shards) have a test in `tests/test_xray.py`
- [ ] `scripts/` still uses the standard library only
- [ ] Skills and agents still cite a `file:line` for every claim
- [ ] If a file copied from code-modernization changed, its `MODIFIED by CODE Éxitos` header and `NOTICE` are up to date
- [ ] `version` in `.claude-plugin/plugin.json` is bumped if installed users are affected
- [ ] `README.md` is updated if usage changed
