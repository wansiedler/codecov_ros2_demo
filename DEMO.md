# Codecov walkthrough

A short script for demonstrating what Codecov adds to a ROS 2 C++ project.

## 0. Prerequisites

* The repository is on GitHub.
* The repository is enabled on <https://codecov.io> and the upload token is
  stored as the GitHub Actions secret `CODECOV_TOKEN`.

## 1. The history on `main`

```text
feat(nav_utils): add velocity limiter with unit tests   <- library + full tests
ci: run tests under gcov and publish coverage to Codecov <- coverage pipeline
feat(nav_utils): add battery monitor                     <- new code, NO tests
test(nav_utils): cover battery monitor                   <- tests added
```

On the Codecov dashboard this shows up as a coverage graph that drops on the
third commit and recovers on the fourth. That is the core message: coverage is
measured per commit, so a regression is visible immediately instead of at the
next release.

Talking points per commit:

| Commit | Coverage | What Codecov shows |
| --- | --- | --- |
| `feat: velocity limiter` | – | No report: the CI pipeline does not exist yet at this commit. |
| `ci: ...` | **100 %** (19/19 lines) | First upload; sunburst and file tree become available. |
| `feat: battery monitor` | **43.18 %** (19/44) | Coverage collapses, `battery_monitor.cpp` is fully red. |
| `test: cover battery monitor` | **97.82 %** (45/46) | Back to green; the one miss is the unreachable `return "UNKNOWN";` guard. |

These are the numbers the pipeline actually reported, not estimates.

## 2. The pull request demo (the part that convinces people)

The branch `feat/safety-zones` adds a `SafetyZone` class with only one of its
branches tested.

```bash
git push -u origin feat/safety-zones
gh pr create --fill
```

Once CI finishes, Codecov comments on the pull request:

* the **patch** status fails, because far less than 80 % of the newly added
  lines are covered (`codecov.yml` → `coverage.status.patch.target: 80%`);
* the diff view marks each uncovered line in the pull request itself, so the
  reviewer sees exactly which branches were never executed.

Then push the follow-up commit that adds the missing tests:

```bash
git merge --ff-only demo/safety-zones-tests   # or: git cherry-pick demo/safety-zones-tests
git push
```

CI re-runs, Codecov updates its comment, and both the project and the patch
status turn green. This is the loop worth showing: the tool does not just
report a number, it blocks untested code from being merged.

## 3. Where the numbers come from

Nothing in this setup is Codecov-specific magic:

1. `-DCOVERAGE=ON` adds `--coverage` to the compile and link flags, so GCC
   writes `.gcno` (structure) and `.gcda` (counters) files next to the objects.
2. `colcon test` executes the gtest binaries, which fills the counters.
3. `lcov` captures a baseline from the `.gcno` files (`--capture --initial`),
   captures the executed counters, and merges both into a single
   `coverage.info`, then strips system headers, gtest internals and the tests.
   The baseline matters: a source file that no test ever touches has no `.gcda`
   at all, and without the baseline it would silently vanish from the report
   instead of showing up as 0 % covered.
4. `codecov/codecov-action@v5` uploads that file and attaches it to the commit
   SHA, which is how Codecov can compare a pull request against its base.

The same pipeline runs locally, so a developer can check the report before
pushing (`genhtml coverage.info -o coverage_html`).

## 4. Rules currently enforced (`codecov.yml`)

| Rule | Value | Effect |
| --- | --- | --- |
| `project` | `auto`, threshold 1 % | Total coverage may not fall more than 1 % below the base commit. |
| `patch` | 80 % | At least 80 % of the lines changed by a PR must be covered. |
| `ignore` | `*_node.cpp`, tests | Thin rclcpp wiring is not counted, so the number reflects testable logic. |

Both thresholds are deliberately conservative: the goal is to prevent new
untested code, not to force an existing codebase to 100 % overnight.
