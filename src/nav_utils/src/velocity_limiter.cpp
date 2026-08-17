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

VelocityLimiter::VelocityLimiter(const VelocityLimits & limits)
: limits_(limits)
{
}

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

void VelocityLimiter::reset()
{
  last_ = Twist2D{};
}

}  // namespace nav_utils
