# Security Checklist

Based on the OWASP Top 10 (2021) and OWASP ASVS 5.0 (current as of 2025), adapted to a PR-diff
review context. OWASP's 2026 Top 10 update elevates software supply chain risk to its own
top-level category (Software Supply Chain Failures) — item 9 below already covers it explicitly
for that reason, rather than leaving it folded into "known vulnerabilities" alone. Used by the
`security-reviewer` agent on every PR.

## OWASP Top 10 Review Items

1. **Injection** — SQL/NoSQL/command/LDAP injection: are all external inputs parameterized or escaped, never string-concatenated into a query/command?

2. **Broken authentication** — session tokens generated securely, expired/invalidated correctly, no credentials in logs or error messages, no weak password/reset flows introduced.

3. **Sensitive data exposure** — PII/secrets never logged, never in URL query params, encrypted at rest and in transit where required, no secrets committed to the repo (check for hardcoded keys/tokens).

4. **XML External Entities (XXE)** — if XML parsing is introduced, external entity resolution is disabled.

5. **Broken access control** — every new endpoint/action checks authorization, not just authentication; no reliance on client-side checks alone; object-level authorization checked (can user A access user B's resource by ID manipulation?).

6. **Security misconfiguration** — no debug mode/stack traces exposed in production paths, default credentials never shipped, unnecessary services/ports not opened, CORS not wildcarded unless justified.

7. **Cross-Site Scripting (XSS)** — all user-controlled output is escaped/sanitized for its output context (HTML, JS, URL, attribute).

8. **Insecure deserialization** — no deserialization of untrusted data without validation; prefer safe formats (JSON over pickled/serialized objects) for untrusted boundaries.

9. **Using components with known vulnerabilities / software supply chain** — new dependencies checked against known CVEs (via `bun audit`/equivalent + CodeRabbit's dependency scan) before merge; versions pinned, not left floating on a range that can silently resolve to a compromised release; a third-party package's install/build scripts are treated as untrusted code, not just its published API.

10. **Insufficient logging & monitoring** — auth failures, access-control failures, and input-validation failures are logged (without logging the sensitive payload itself) so incidents are detectable after the fact.

## Additional Requirements

- **Secrets handling** — env vars/secret manager only; never hardcoded or committed.
- **Input validation** — validate at every trust boundary.
- **Output encoding** — matched to context (HTML, JS, URL, attribute).
- **Least privilege** — any new IAM/permission grant follows principle of least privilege.

## Severity Classification

Classify every finding using `resources/standards/severity-classification.md`. Critical and High security findings block merge.
