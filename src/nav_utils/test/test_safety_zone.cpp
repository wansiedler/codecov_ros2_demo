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

#include <gtest/gtest.h>

#include "nav_utils/safety_zone.hpp"

using nav_utils::SafetyZone;
using nav_utils::Zone;
using nav_utils::ZoneRadii;

TEST(SafetyZone, ClassifiesClearSpace)
{
  const SafetyZone zone{ZoneRadii{}};

  EXPECT_EQ(zone.classify(3.0), Zone::Clear);
  EXPECT_DOUBLE_EQ(zone.speed_scale(3.0), 1.0);
}

TEST(SafetyZone, ClassifiesWarningZone)
{
  const SafetyZone zone{ZoneRadii{}};

  EXPECT_EQ(zone.classify(1.2), Zone::Warning);
  EXPECT_DOUBLE_EQ(zone.speed_scale(1.2), 0.6);
}

TEST(SafetyZone, ClassifiesDangerZone)
{
  const SafetyZone zone{ZoneRadii{}};

  EXPECT_EQ(zone.classify(0.5), Zone::Danger);
  EXPECT_DOUBLE_EQ(zone.speed_scale(0.5), 0.25);
}

TEST(SafetyZone, StopsInsideStopRadius)
{
  const SafetyZone zone{ZoneRadii{}};

  EXPECT_EQ(zone.classify(0.1), Zone::Stop);
  EXPECT_DOUBLE_EQ(zone.speed_scale(0.1), 0.0);
}

TEST(SafetyZone, AppliesScalingToVelocity)
{
  const SafetyZone zone{ZoneRadii{}};

  EXPECT_DOUBLE_EQ(zone.apply(1.0, 3.0), 1.0);
  EXPECT_DOUBLE_EQ(zone.apply(1.0, 1.2), 0.6);
  EXPECT_DOUBLE_EQ(zone.apply(0.8, 0.5), 0.2);
  EXPECT_DOUBLE_EQ(zone.apply(1.0, 0.1), 0.0);
}

TEST(SafetyZone, HonoursCustomRadii)
{
  ZoneRadii radii;
  radii.stop = 0.5;
  radii.danger = 1.0;
  radii.warning = 2.0;
  const SafetyZone zone{radii};

  EXPECT_EQ(zone.classify(0.4), Zone::Stop);
  EXPECT_EQ(zone.classify(0.9), Zone::Danger);
  EXPECT_EQ(zone.classify(1.8), Zone::Warning);
  EXPECT_EQ(zone.classify(2.5), Zone::Clear);
}
