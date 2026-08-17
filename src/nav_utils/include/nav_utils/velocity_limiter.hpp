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

#ifndef NAV_UTILS__VELOCITY_LIMITER_HPP_
#define NAV_UTILS__VELOCITY_LIMITER_HPP_

namespace nav_utils
{

/// Velocity command expressed in the robot base frame.
struct Twist2D
{
  double linear{0.0};   ///< m/s, forward positive
  double angular{0.0};  ///< rad/s, counter-clockwise positive
};

/// Static limits applied to every command.
struct VelocityLimits
{
  double max_linear{1.0};        ///< m/s
  double max_angular{1.0};       ///< rad/s
  double max_linear_accel{0.5};  ///< m/s^2
};

/// Clamps velocity commands to configured limits and ramps linear velocity
/// so the vehicle never exceeds the maximum acceleration.
class VelocityLimiter
{
public:
  explicit VelocityLimiter(const VelocityLimits & limits);

  /// Limits @p command given the time @p dt elapsed since the previous call.
  /// A non-positive @p dt disables the acceleration ramp for that call.
  Twist2D limit(const Twist2D & command, double dt);

  /// Drops the acceleration history, e.g. after an emergency stop.
  void reset();

  /// Last velocity returned by limit().
  [[nodiscard]] Twist2D last() const { return last_; }

private:
  VelocityLimits limits_;
  Twist2D last_{};
};

}  // namespace nav_utils

#endif  // NAV_UTILS__VELOCITY_LIMITER_HPP_
