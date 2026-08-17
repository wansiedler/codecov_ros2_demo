# codecov_ros2_demo

A minimal ROS 2 (Jazzy) C++ workspace used to demonstrate how [Codecov](https://about.codecov.io/)
reports test coverage on every commit and pull request.

[![CI](https://github.com/wansiedler/codecov_ros2_demo/actions/workflows/ci.yml/badge.svg)](https://github.com/wansiedler/codecov_ros2_demo/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/wansiedler/codecov_ros2_demo/graph/badge.svg?token=CT2tkB1DJ4)](https://codecov.io/gh/wansiedler/codecov_ros2_demo)

## Coverage at a glance

The graphs below are served live by Codecov and update with every upload.
Size encodes the number of statements, colour encodes coverage.

| Sunburst | Grid | Icicle |
| --- | --- | --- |
| [<img src="https://codecov.io/gh/wansiedler/codecov_ros2_demo/graphs/sunburst.svg?token=CT2tkB1DJ4" width="220" alt="Coverage sunburst">](https://codecov.io/gh/wansiedler/codecov_ros2_demo) | [<img src="https://codecov.io/gh/wansiedler/codecov_ros2_demo/graphs/tree.svg?token=CT2tkB1DJ4" width="220" alt="Coverage grid">](https://codecov.io/gh/wansiedler/codecov_ros2_demo) | [<img src="https://codecov.io/gh/wansiedler/codecov_ros2_demo/graphs/icicle.svg?token=CT2tkB1DJ4" width="220" alt="Coverage icicle">](https://codecov.io/gh/wansiedler/codecov_ros2_demo) |

* **Sunburst** — innermost ring is the whole project, outward rings are folders
  and finally single files.
* **Grid** — one block per file.
* **Icicle** — same hierarchy as the sunburst, laid out top to bottom.

## What is in here

```
src/nav_utils/
├── include/nav_utils/velocity_limiter.hpp   # clamping + acceleration ramp
├── include/nav_utils/battery_monitor.hpp    # battery state classification
├── src/velocity_limiter.cpp
├── src/battery_monitor.cpp
├── src/velocity_limiter_node.cpp            # rclcpp node (excluded from coverage)
└── test/                                    # ament_cmake_gtest unit tests
```

The package is deliberately small: pure C++ classes with unit tests, plus one
ROS node that wires them to topics. That is enough to produce a realistic coverage
report without needing a robot.

## How coverage is produced

1. CI builds the workspace with `-DCOVERAGE=ON`, which adds `--coverage` to the
   compiler and linker flags, so GCC emits `.gcno` / `.gcda` profiling files.
2. `colcon test` runs the gtest suites, which fills the `.gcda` counters.
3. `lcov` collects the counters into `coverage.info` and strips system headers,
   gtest internals and the test sources themselves.
4. `codecov/codecov-action@v5` uploads `coverage.info` to Codecov.

`codecov.yml` then enforces two checks on every pull request:

| Check | Meaning |
| --- | --- |
| `project` | Total coverage must not drop more than 1 % below the base commit. |
| `patch` | At least 80 % of the lines *changed in the PR* must be covered. |

## Quality gates

Everything below runs on every pull request; the slow jobs also run on a schedule.

| Layer | Tooling | Where |
| --- | --- | --- |
| Formatting | `clang-format` (ROS 2 profile in `.clang-format`), `ament_clang_format` | pre-commit + `Lint` workflow |
| Style linting | `cpplint`, `ament_cpplint`, `cmake-lint`, `ament_lint_cmake`, `yamllint`, `actionlint`, `codespell` | pre-commit + `Lint` |
| Static analysis | `cppcheck` / `ament_cppcheck`, `clang-tidy` (`.clang-tidy`, warnings are errors) | pre-commit + `Lint` |
| Licence headers | `ament_copyright` | `Lint` |
| Package manifests | `ament_xmllint` | `Lint` |
| Secrets | `gitleaks` (working tree in pre-commit, full history in CI) | pre-commit + `Security` |
| Code scanning | CodeQL `security-and-quality`, Trivy (`vuln,secret,misconfig`), OpenSSF Scorecard | `Security` |
| Dependencies | Dependabot for GitHub Actions | `.github/dependabot.yml` |
| Runtime analysis | ASan + UBSan, TSan, Valgrind memcheck | `Runtime analysis` |
| Coverage | gcov → lcov → Codecov | `CI` |

CodeQL, Trivy and Scorecard publish SARIF, so their findings land in the
repository's **Security → Code scanning** tab instead of only in a log.

### Local setup

```bash
pipx install pre-commit      # or: pip install --user pre-commit
pre-commit install           # run the hooks on every commit
pre-commit run --all-files   # run them over the whole tree once
```

Sanitizer and memcheck builds are plain CMake options, so the same checks run
locally:

```bash
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DSANITIZE=address,undefined
colcon test
valgrind --leak-check=full build/nav_utils/test_velocity_limiter
```

## Setup (one time)

1. Push this repository to GitHub.
2. Sign in to <https://codecov.io> with the GitHub account and enable the repository.
3. Copy the upload token from Codecov and store it in the repository as the
   secret `CODECOV_TOKEN` (Settings → Secrets and variables → Actions).
4. Push a commit or open a pull request — the CI workflow uploads the report and
   Codecov comments on the PR.

## Running the tests locally

Requires ROS 2 Jazzy and `lcov`:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DCOVERAGE=ON
colcon test
colcon test-result --verbose
lcov --capture --directory build --output-file coverage.info \
  --ignore-errors mismatch,gcov,unused,empty,negative
lcov --extract coverage.info "$PWD/src/*" --output-file coverage.info
genhtml coverage.info --output-directory coverage_html   # open coverage_html/index.html
```

Running the node:

```bash
source install/setup.bash
ros2 run nav_utils velocity_limiter_node --ros-args -p max_linear:=0.8
```
