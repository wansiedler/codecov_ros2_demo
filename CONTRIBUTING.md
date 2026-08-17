# Contributing

## Local setup

```bash
pipx install pre-commit
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg   # enables the commitizen check
```

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
