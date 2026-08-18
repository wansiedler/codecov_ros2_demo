#!/bin/bash -eu
# Builds every fuzz target against the ROS-free core of the package.
#
# nav_utils_core has no rclcpp dependency on purpose, so the targets compile
# with the plain toolchain instead of dragging a ROS install into the image.
# The sources use nothing newer than C++20 (std::numbers, ranges), which keeps
# them buildable with whatever clang the base image carries.

SRC_DIR="$SRC/codecov_ros2_demo/src/nav_utils"

for target in "$SRC_DIR"/fuzz/fuzz_*.cpp; do
  name="$(basename "$target" .cpp)"
  echo "building $name"
  # shellcheck disable=SC2086
  $CXX $CXXFLAGS -std=c++20 \
    -I"$SRC_DIR/include" \
    "$target" \
    "$SRC_DIR/src/velocity_limiter.cpp" \
    "$SRC_DIR/src/battery_monitor.cpp" \
    "$SRC_DIR/src/safety_zone.cpp" \
    "$SRC_DIR/src/pure_pursuit.cpp" \
    $LIB_FUZZING_ENGINE \
    -o "$OUT/$name"
done
