# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Report it privately, either way works:

- **GitHub:** use [Report a vulnerability](https://github.com/code-exitos/codebase-xray/security/advisories/new)
  on the repository's Security tab.
- **Email:** security@codexitos.com

Include what you found, the file or skill involved, how to reproduce it, and what an attacker
could do with it. We will acknowledge your report within 5 business days, keep you posted while
we fix it, and credit you in the advisory unless you would rather stay anonymous.

## What is in scope

- `scripts/xray.py` and `scripts/render_rules.py`, which read and write files in the codebase
  being analyzed.
- The skills, agents and workflow, for example a prompt or path that makes an agent read or
  write outside the target codebase, or run commands it should not.

Findings *about the codebase you analyzed* (what `security-sweep` reports) are not
vulnerabilities in this plugin. A wrong or missed finding from `security-sweep` is a bug: open a
normal issue.

## Supported versions

Only the latest release on `main` gets security fixes.
