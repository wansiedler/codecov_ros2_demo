# codecov_ros2_demo

A minimal ROS 2 (Jazzy) C++ workspace used to demonstrate how [Codecov](https://about.codecov.io/)
reports test coverage on every commit and pull request.

[![CI](https://github.com/OWNER/codecov_ros2_demo/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/codecov_ros2_demo/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/OWNER/codecov_ros2_demo/branch/main/graph/badge.svg)](https://codecov.io/gh/OWNER/codecov_ros2_demo)

> Replace `OWNER` in the badge URLs with the GitHub account or organisation that hosts the repository.

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
