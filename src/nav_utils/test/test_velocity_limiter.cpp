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

#include "nav_utils/velocity_limiter.hpp"

using nav_utils::Twist2D;
using nav_utils::VelocityLimiter;
using nav_utils::VelocityLimits;

namespace
{
VelocityLimits default_limits()
{
  VelocityLimits limits;
  limits.max_linear = 1.0;
  limits.max_angular = 2.0;
  limits.max_linear_accel = 0.5;
  return limits;
}
}  // namespace

TEST(VelocityLimiter, PassesCommandInsideLimits)
{
  VelocityLimiter limiter(default_limits());

  const Twist2D out = limiter.limit({0.2, 0.3}, 0.0);

  EXPECT_DOUBLE_EQ(out.linear, 0.2);
  EXPECT_DOUBLE_EQ(out.angular, 0.3);
}

TEST(VelocityLimiter, ClampsLinearVelocity)
{
  VelocityLimiter limiter(default_limits());

  EXPECT_DOUBLE_EQ(limiter.limit({5.0, 0.0}, 0.0).linear, 1.0);
  EXPECT_DOUBLE_EQ(limiter.limit({-5.0, 0.0}, 0.0).linear, -1.0);
}

TEST(VelocityLimiter, ClampsAngularVelocity)
{
  VelocityLimiter limiter(default_limits());

  EXPECT_DOUBLE_EQ(limiter.limit({0.0, 9.0}, 0.0).angular, 2.0);
  EXPECT_DOUBLE_EQ(limiter.limit({0.0, -9.0}, 0.0).angular, -2.0);
}

TEST(VelocityLimiter, RampsLinearVelocityWithAccelerationLimit)
{
  VelocityLimiter limiter(default_limits());

  // 0.5 m/s^2 over 0.1 s allows a 0.05 m/s step, not the requested 1.0 m/s.
  EXPECT_DOUBLE_EQ(limiter.limit({1.0, 0.0}, 0.1).linear, 0.05);
  EXPECT_DOUBLE_EQ(limiter.limit({1.0, 0.0}, 0.1).linear, 0.10);
}

TEST(VelocityLimiter, RampsDecelerationAsWell)
{
  VelocityLimiter limiter(default_limits());
  limiter.limit({1.0, 0.0}, 0.0);  // jump straight to 1.0 m/s

  EXPECT_DOUBLE_EQ(limiter.limit({0.0, 0.0}, 0.2).linear, 0.9);
}

TEST(VelocityLimiter, ResetClearsHistory)
{
  VelocityLimiter limiter(default_limits());
  limiter.limit({1.0, 0.0}, 0.0);
  ASSERT_DOUBLE_EQ(limiter.last().linear, 1.0);

  limiter.reset();

  EXPECT_DOUBLE_EQ(limiter.last().linear, 0.0);
  EXPECT_DOUBLE_EQ(limiter.limit({1.0, 0.0}, 0.1).linear, 0.05);
}
