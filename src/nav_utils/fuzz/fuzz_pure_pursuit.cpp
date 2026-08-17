// Copyright 2026 Alexander Paul Wansiedler
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Feeds arbitrary poses and paths to the controller. A path comes from a
// localisation stack and a planner, so NaN, infinities and coincident points
// are all reachable in the field - the controller must stay finite or say it
// has nothing to steer at.

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <utility>
#include <vector>

#include "nav_utils/pure_pursuit.hpp"

namespace
{

/// Reads values out of the fuzzer input, wrapping around when it runs out.
class Reader
{
public:
  Reader(const uint8_t * data, size_t size) : data_(data), size_(size) {}

  double next_double()
  {
    if (size_ < sizeof(double)) {
      return 0.0;
    }
    double value = 0.0;
    std::memcpy(&value, data_ + offset_, sizeof(value));
    offset_ = (offset_ + sizeof(value)) % (size_ - sizeof(double) + 1);
    return value;
  }

private:
  const uint8_t * data_;
  size_t size_;
  size_t offset_{0};
};

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t * data, size_t size)
{
  if (size < sizeof(double) * 4) {
    return 0;
  }

  Reader reader(data, size);

  nav_utils::PurePursuitConfig config;
  config.lookahead = reader.next_double();
  config.max_angular = reader.next_double();
  config.goal_tolerance = reader.next_double();

  nav_utils::PurePursuit controller{config};

  const size_t points = (size / sizeof(double)) % 64U;
  std::vector<nav_utils::Point2D> path;
  path.reserve(points);
  for (size_t i = 0; i < points; ++i) {
    path.push_back({reader.next_double(), reader.next_double()});
  }
  controller.set_path(std::move(path));

  const nav_utils::Pose2D pose{reader.next_double(), reader.next_double(), reader.next_double()};

  static_cast<void>(controller.at_goal(pose));
  static_cast<void>(controller.lookahead_point(pose));
  static_cast<void>(controller.curvature(pose));

  const auto command = controller.angular_velocity(pose, reader.next_double());

  // The contract, checked unconditionally: whatever the input, a command that
  // exists is finite, and it stays inside the bound whenever the bound itself
  // is finite. A NaN steering rate compares false against every limit
  // downstream, so it must never leave the controller.
  if (command.has_value()) {
    if (!std::isfinite(*command)) {
      __builtin_trap();
    }
    if (std::isfinite(config.max_angular)) {
      const double bound = std::abs(config.max_angular);
      if (std::abs(*command) > bound + 1e-9) {
        __builtin_trap();
      }
    }
  }

  return 0;
}
