# Governance

## Model

`perfect_ros2_atomic_package` is a single-maintainer project. The maintainer
takes every decision about scope, design and releases, in the open: a change
is proposed as a pull request, discussed on it, and merged or closed there.
There is no separate steering body, and nothing is decided in private channels.

## Roles

| Role | Who | Responsibilities |
| --- | --- | --- |
| Maintainer | [@wansiedler](https://github.com/wansiedler) (`CODEOWNERS`) | Reviews and merges pull requests, triages issues and vulnerability reports, cuts releases, holds the repository settings and the CI secrets |
| Contributor | Anyone | Opens issues and pull requests following [CONTRIBUTING.md](CONTRIBUTING.md); keeps a change tested, formatted and conventionally described |
| Reporter | Anyone | Reports bugs through issues and vulnerabilities through [SECURITY.md](SECURITY.md) |

Code review is required for every change to `main`, including the
maintainer's own: the branch is protected, the pull request must be up to date
and every required check green before it can merge. What a review looks for is
written down in [CONTRIBUTING.md](CONTRIBUTING.md#code-review).

## Decisions

- **Scope and design** - proposed in an issue or a pull request, decided by
  the maintainer on the thread. The [roadmap](ROADMAP.md) records what is in
  and out of scope for the year.
- **Releases** - cut by release-please from the Conventional Commits on `main`;
  the maintainer merges the release pull request. The version follows
  [SemVer](https://semver.org): `feat` bumps minor, `fix` bumps patch, a
  `BREAKING CHANGE` footer bumps major.
- **Dependencies** - Dependabot proposes updates; the maintainer merges them
  once CI is green. Anything that changes a pin by hand goes through the same
  review.

## Supported versions and upgrades

Only the latest release is supported. A fix lands on `main` and ships in the
next release; there are no maintenance branches for older versions. Breaking
changes are announced in [CHANGELOG.md](CHANGELOG.md) under *BREAKING CHANGES*
with what changed in the interface and what a user has to do, so an upgrade
from any earlier release is one read of the changelog.

## Continuity

A single maintainer is a bus factor of one, and this file does not pretend
otherwise. Everything needed to continue the project is in the repository
itself - the build, the tests, the release pipeline, the CI configuration - and
nothing depends on a key held outside GitHub: releases are signed keylessly
with the workflow's own identity, and the container image lives in GHCR under
the repository. Handing the project over is adding a second owner with the
GitHub repository settings; no secret has to travel.
