# Contributing

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

## Before opening a pull request

```bash
pre-commit run --all-files
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DCOVERAGE=ON
colcon test && colcon test-result --verbose
```

New or changed lines need at least 80 % coverage, otherwise the Codecov patch
status fails the pull request.
