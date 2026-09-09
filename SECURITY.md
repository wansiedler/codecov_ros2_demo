# Security policy

## Supported versions

Only the latest release and `main` receive security fixes; a fix ships as a
new release. See [GOVERNANCE.md](GOVERNANCE.md#supported-versions-and-upgrades).

## Reporting a vulnerability

Please report suspected vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/wansiedler/perfect_ros2_atomic_package/security/advisories/new)
rather than a public issue. Expect an acknowledgement within five working days,
an assessment within fifteen, and a fix within ninety days of the report; the
advisory is published with the fixed release, with credit to the reporter
unless they prefer otherwise. The full coordinated-disclosure policy, the
remediation thresholds and the secrets policy are in
[docs/security.md](docs/security.md#policies). Published advisories:
<https://github.com/wansiedler/perfect_ros2_atomic_package/security/advisories>.

Security contact: the maintainer, [@wansiedler](https://github.com/wansiedler),
through the private reporting link above.

## Automated scanning

Every pull request runs CodeQL (`security-and-quality`), Trivy, Semgrep,
OSV-Scanner, gitleaks and OpenSSF Scorecard. Findings are published as SARIF and
appear under **Security → Code scanning**.
