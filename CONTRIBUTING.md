# Contributing

Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Local setup

```bash
pipx install pre-commit
pre-commit install --install-hooks
```

One command is enough: `default_install_hook_types` in the config wires all
three stages - the file checks before the commit, the message check on the
message itself, and a check of the whole range before a push.

## Commit messages

The repository follows [Conventional Commits](https://www.conventionalcommits.org/).
`commitizen` enforces this locally through the `commit-msg` hook and again in CI,
and the pull request title has to follow the same convention because merges are
squashed. Use `cz commit` if you want an interactive prompt.

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.

## Developer Certificate of Origin

Every commit must be signed off:

```bash
git commit -s
```

That adds a `Signed-off-by: Your Name <you@example.com>` trailer, by which you
certify the [Developer Certificate of Origin](https://developercertificate.org)
- that you wrote the change or have the right to submit it under the project's
Apache-2.0 license. No CLA, no paperwork: the trailer is the assertion. The
`commit-msg` hook rejects a commit without it, and the `Conventions` workflow
checks every commit of a pull request.

## Before opening a pull request

```bash
pre-commit run --all-files
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DCOVERAGE=ON
colcon test && colcon test-result --verbose
```

New or changed lines need at least 80 % coverage, otherwise the Codecov patch
status fails the pull request.

## Coding standards

- **C++**: the [ROS 2 C++ style](https://docs.ros.org/en/jazzy/The-ROS2-Project/Contributing/Code-Style-Language-Versions.html)
  as encoded in `.clang-format` and `.clang-tidy`, C++23. `clang-format`,
  `cpplint`, `cppcheck` and `clang-tidy` (warnings are errors) enforce it in
  pre-commit and in CI; `ament_lint` runs the ROS variants as tests.
- **Python**: `ruff` (format and lint, `ruff.toml`) and `bandit`.
- **CMake**: `cmake-lint` and `ament_lint_cmake`.
- **Shell, YAML, Markdown, workflows**: `shellcheck`, `yamllint`,
  `markdownlint`, `actionlint`, `zizmor`.
- Every source file starts with the copyright line and
  `SPDX-License-Identifier: Apache-2.0`; `scripts/check_spdx.py` enforces it.

Nothing is enforced by convention alone: if a rule matters, a hook or a CI job
checks it.

## Tests

Tests are not optional. New functionality lands with tests that exercise it,
and a bug fix lands with a regression test that fails without the fix. This is
policy, checked two ways: the Codecov patch status (80 % of changed lines) and
the reviewer, who reads the tests before the code.

- Unit tests: gtest, one file per component in `src/nav_utils/test/`.
- Integration tests: `launch_testing`, driving the node over real topics.
- Both run with `make test`; coverage with `make coverage`.

## Code review

Every change to `main` is a pull request reviewed before merge - the branch is
protected and requires an up-to-date branch and green checks. A review
confirms, in this order:

1. **Intent** - the pull request says why, not only what; the title is a
   Conventional Commit.
2. **Tests** - new behaviour has tests, a fix has its regression test, and
   the coverage report shows the changed lines exercised.
3. **Security impact** - inputs from outside the package are validated; no
   new dependency, permission or secret without a reason in the description;
   a changed pin comes with its digest.
4. **Checks** - every required check green; a finding from a scanner is fixed
   or explained on the thread, never dismissed silently.
5. **Scope** - one concern per pull request; unrelated cleanups go to their
   own.

The maintainer reviews every pull request, including their own before merging
it. A change that fails any point above is not merged until it passes; the
thread records why.
