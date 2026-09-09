# Architecture

## Overview

One ROS 2 package, `nav_utils`, built with `ament_cmake`. It contains a
library of four pure C++ components with no ROS dependency and one node that
wraps one of them. The split is deliberate: the library is unit-tested with
gtest without an executor, the node is integration-tested with `launch_testing`
over real topics.

```text
src/nav_utils
├── include/nav_utils/     public interface, one header per component
│   ├── velocity_limiter.hpp
│   ├── battery_monitor.hpp
│   ├── safety_zone.hpp
│   └── pure_pursuit.hpp
├── src/
│   ├── *.cpp              the four components -> libnav_utils_core.a
│   └── velocity_limiter_node.cpp   the node  -> velocity_limiter_node
├── test/                  gtest per component + test_velocity_limiter_node.py
└── fuzz/                  libFuzzer targets (built with -DFUZZING=ON)
```

## Components

| Component | Input | Output | Invariants it guards |
| --- | --- | --- | --- |
| `VelocityLimiter` | `Twist2D` command, elapsed time `dt` | `Twist2D` | linear and angular speed within `VelocityLimits`; linear acceleration ramped; non-positive `dt` disables the ramp for that call |
| `BatteryMonitor` | pack voltage | `BatteryState` (Ok / Low / Critical), state of charge in % | linear 3.2-4.2 V per cell estimate, clamped to [0, 100]; non-finite voltage reads as empty; unknown state stringifies as `UNKNOWN` |
| `SafetyZone` | distance to the closest obstacle | `Zone` (Clear / Warning / Danger / Stop), speed scale in [0, 1] | an unrecognised zone scales to a full stop |
| `PurePursuit` | `Pose2D`, a path of `Point2D` | lookahead point, curvature, angular velocity | non-finite geometry yields no command; NaN points cannot break the ordering the search relies on |

All four are plain value types: no threads, no I/O, no global state, no
exceptions thrown on their own. Every input the outside world can hand them
is validated at the boundary (see [security.md](security.md)).

## The node

`velocity_limiter_node` owns one `VelocityLimiter`:

```text
cmd_vel_raw (geometry_msgs/Twist) --> [VelocityLimiter] --> cmd_vel (geometry_msgs/Twist)
```

- Parameters: `max_linear`, `max_angular`, `max_linear_accel` (declared with
  the library's defaults, read once at start).
- The elapsed time between commands is computed on the node's own clock in
  nanoseconds, so no clock-source mismatch can throw inside the callback.
- One subscription, one publisher, queue depth 10, default executor.

## Build and test flow

```text
colcon build  -> libnav_utils_core.a, velocity_limiter_node, test_* binaries
colcon test   -> gtest (unit) + launch_testing (integration) + ament linters
lcov          -> coverage.info (exception edges stripped) -> Codecov, HTML
```

The same `Makefile` targets run on a developer machine, in the dev container
(`make docker-test`) and in CI, so the three cannot drift. What each CI lane
adds on top - sanitizers, valgrind, fuzzing, static analysis, signed releases -
is listed in the README's *Quality gates* table.
