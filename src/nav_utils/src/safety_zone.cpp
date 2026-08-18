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

#include "nav_utils/safety_zone.hpp"

#include <algorithm>

namespace nav_utils
{

SafetyZone::SafetyZone(const ZoneRadii & radii) : radii_(radii) {}

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
  return speed_scale(classify(obstacle_distance));
}

double SafetyZone::speed_scale(Zone zone)
{
  switch (zone) {
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
