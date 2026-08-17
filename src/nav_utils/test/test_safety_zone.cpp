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
