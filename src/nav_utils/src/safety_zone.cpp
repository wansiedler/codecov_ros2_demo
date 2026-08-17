#include "nav_utils/safety_zone.hpp"

#include <algorithm>

namespace nav_utils
{

SafetyZone::SafetyZone(const ZoneRadii & radii)
: radii_(radii)
{
}

Zone SafetyZone::classify(double obstacle_distance) const
{
  if (obstacle_distance <= radii_.stop) {
    return Zone::Stop;
  }
  if (obstacle_distance <= radii_.danger) {
    return Zone::Danger;
  }
  if (obstacle_distance <= radii_.warning) {
    return Zone::Warning;
  }
  return Zone::Clear;
}

double SafetyZone::speed_scale(double obstacle_distance) const
{
  switch (classify(obstacle_distance)) {
    case Zone::Stop:
      return 0.0;
    case Zone::Danger:
      return 0.25;
    case Zone::Warning:
      return 0.6;
    case Zone::Clear:
      return 1.0;
  }
  return 0.0;
}

double SafetyZone::apply(double velocity, double obstacle_distance) const
{
  return velocity * speed_scale(obstacle_distance);
}

}  // namespace nav_utils
