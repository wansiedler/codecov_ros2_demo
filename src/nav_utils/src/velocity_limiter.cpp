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

#include "nav_utils/velocity_limiter.hpp"

#include <algorithm>
#include <cmath>

namespace nav_utils
{

namespace
{
double clamp_symmetric(double value, double limit)
{
  const double bound = std::abs(limit);
  return std::max(-bound, std::min(bound, value));
}
}  // namespace

VelocityLimiter::VelocityLimiter(const VelocityLimits & limits) : limits_(limits) {}

Twist2D VelocityLimiter::limit(const Twist2D & command, double dt)
{
  Twist2D out;
  out.linear = clamp_symmetric(command.linear, limits_.max_linear);
  out.angular = clamp_symmetric(command.angular, limits_.max_angular);

  if (dt > 0.0) {
    const double max_delta = limits_.max_linear_accel * dt;
    const double delta = out.linear - last_.linear;
    if (std::abs(delta) > max_delta) {
      out.linear = last_.linear + std::copysign(max_delta, delta);
    }
  }

  last_ = out;
  return out;
}

void VelocityLimiter::reset() { last_ = Twist2D{}; }

}  // namespace nav_utils
