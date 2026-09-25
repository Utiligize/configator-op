# Security Policy

Configator loads configuration and secrets for downstream applications, so we
take security reports seriously.

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Report privately through GitHub's [private vulnerability reporting][gh-pvr] on
this repository: go to the **Security** tab and click **Report a vulnerability**.
This opens a confidential advisory visible only to you and the maintainers.

If you cannot use GitHub advisories, email <contact@utiligize.com> instead.

Please include enough detail to reproduce the issue: affected version, a
description of the impact, and steps or a proof of concept. We aim to acknowledge
reports within five business days and will keep you informed as we work on a fix.

## Published Advisories

Advisories are listed on the repository's [security advisories][gh-advisories]
page. Releases pulled because of an advisory are yanked from PyPI and marked
`[YANKED]` in [CHANGELOG.md](CHANGELOG.md).

- [GHSA-3rmr-35mv-wrrp][ghsa-3rmr-35mv-wrrp]: 3000.6.0 and 3000.7.0 log the
  1Password service-account token when authentication is retried. Fixed in
  3000.7.1.

## Supported Versions

Only the latest released version receives security fixes. Fixes are shipped in a
new release rather than backported; upgrade to the most recent version to stay
protected.

[gh-pvr]: https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability
[gh-advisories]: https://github.com/Utiligize/configator-op/security/advisories
[ghsa-3rmr-35mv-wrrp]: https://github.com/Utiligize/configator-op/security/advisories/GHSA-3rmr-35mv-wrrp
