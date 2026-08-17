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

#include <cmath>
#include <limits>
#include <numbers>
#include <vector>

#include "nav_utils/pure_pursuit.hpp"

using nav_utils::Point2D;
using nav_utils::Pose2D;
using nav_utils::PurePursuit;
using nav_utils::PurePursuitConfig;

namespace
{

constexpr double kTolerance = 1e-9;

// std::numbers::pi instead of the POSIX M_PI macros, which glibc hides
// under a strict -std= setting.
constexpr double kPi = std::numbers::pi;
constexpr double kHalfPi = kPi / 2.0;

PurePursuitConfig default_config()
{
  PurePursuitConfig config;
  config.lookahead = 1.0;
  config.max_angular = 1.5;
  config.goal_tolerance = 0.1;
  return config;
}

/// Straight line along +x, one point every half metre.
std::vector<Point2D> straight_path()
{
  return {{0.5, 0.0}, {1.0, 0.0}, {1.5, 0.0}, {2.0, 0.0}, {2.5, 0.0}};
}

}  // namespace

TEST(PurePursuit, ReportsNoPathUntilOneIsSet)
{
  const PurePursuit controller{default_config()};

  EXPECT_FALSE(controller.has_path());
  EXPECT_EQ(controller.path_size(), 0U);
  EXPECT_FALSE(controller.lookahead_point(Pose2D{}).has_value());
  EXPECT_FALSE(controller.curvature(Pose2D{}).has_value());
  EXPECT_FALSE(controller.angular_velocity(Pose2D{}, 1.0).has_value());
  EXPECT_FALSE(controller.at_goal(Pose2D{}));
}

TEST(PurePursuit, PicksTheFirstPointBeyondTheLookahead)
{
  PurePursuit controller{default_config()};
  controller.set_path(straight_path());

  ASSERT_TRUE(controller.has_path());
  EXPECT_EQ(controller.path_size(), 5U);

  const auto target = controller.lookahead_point(Pose2D{});
  ASSERT_TRUE(target.has_value());
  EXPECT_NEAR(target->x, 1.0, kTolerance);  // 0.5 is closer than the lookahead
  EXPECT_NEAR(target->y, 0.0, kTolerance);
}

TEST(PurePursuit, FallsBackToTheGoalWhenTheRestOfThePathIsShort)
{
  PurePursuit controller{default_config()};
  controller.set_path(straight_path());

  // Standing near the end: every remaining point is inside the lookahead.
  const auto target = controller.lookahead_point(Pose2D{2.4, 0.0, 0.0});
  ASSERT_TRUE(target.has_value());
  EXPECT_NEAR(target->x, 2.5, kTolerance);
}

TEST(PurePursuit, IgnoresPointsBehindTheRobot)
{
  PurePursuit controller{default_config()};
  // The first point lies two metres behind: far enough to satisfy the
  // lookahead, and steering at it would drive the robot backwards.
  controller.set_path({{-2.0, 0.0}, {0.5, 0.0}, {1.5, 0.0}});

  const auto target = controller.lookahead_point(Pose2D{});
  ASSERT_TRUE(target.has_value());
  EXPECT_NEAR(target->x, 1.5, kTolerance);
}

TEST(PurePursuit, DrivesStraightWhenTheTargetIsAhead)
{
  PurePursuit controller{default_config()};
  controller.set_path(straight_path());

  EXPECT_NEAR(*controller.curvature(Pose2D{}), 0.0, kTolerance);
  EXPECT_NEAR(*controller.angular_velocity(Pose2D{}, 0.8), 0.0, kTolerance);
}

TEST(PurePursuit, TurnsLeftForATargetToTheLeft)
{
  PurePursuit controller{default_config()};
  controller.set_path({{0.0, 1.0}});

  // Target one metre to the left: curvature = 2 * y / d^2 = 2.
  const auto arc = controller.curvature(Pose2D{});
  ASSERT_TRUE(arc.has_value());
  EXPECT_NEAR(*arc, 2.0, kTolerance);
  EXPECT_GT(*controller.angular_velocity(Pose2D{}, 0.5), 0.0);
}

TEST(PurePursuit, TurnsRightForATargetToTheRight)
{
  PurePursuit controller{default_config()};
  controller.set_path({{0.0, -1.0}});

  const auto arc = controller.curvature(Pose2D{});
  ASSERT_TRUE(arc.has_value());
  EXPECT_NEAR(*arc, -2.0, kTolerance);
  EXPECT_LT(*controller.angular_velocity(Pose2D{}, 0.5), 0.0);
}

TEST(PurePursuit, AccountsForTheRobotHeading)
{
  PurePursuit controller{default_config()};
  controller.set_path({{0.0, 1.0}});

  // Facing +y, so the point one metre along +y is straight ahead.
  const Pose2D facing_north{0.0, 0.0, kHalfPi};
  EXPECT_NEAR(*controller.curvature(facing_north), 0.0, kTolerance);

  // Facing -x, so the same point now sits to the right.
  const Pose2D facing_west{0.0, 0.0, kPi};
  EXPECT_NEAR(*controller.curvature(facing_west), -2.0, kTolerance);
}

TEST(PurePursuit, ClampsTheAngularVelocity)
{
  PurePursuitConfig config = default_config();
  config.max_angular = 0.4;
  PurePursuit controller{config};
  controller.set_path({{0.0, 0.5}});  // tight arc: curvature = 4

  EXPECT_NEAR(*controller.angular_velocity(Pose2D{}, 1.0), 0.4, kTolerance);
  controller.set_path({{0.0, -0.5}});
  EXPECT_NEAR(*controller.angular_velocity(Pose2D{}, 1.0), -0.4, kTolerance);
}

TEST(PurePursuit, ScalesTheCommandWithTheLinearVelocity)
{
  PurePursuit controller{default_config()};
  controller.set_path({{0.0, 1.0}});  // curvature 2

  EXPECT_NEAR(*controller.angular_velocity(Pose2D{}, 0.25), 0.5, kTolerance);
  EXPECT_NEAR(*controller.angular_velocity(Pose2D{}, 0.0), 0.0, kTolerance);
}

TEST(PurePursuit, StopsTurningAtTheGoal)
{
  PurePursuit controller{default_config()};
  controller.set_path({{1.0, 1.0}});

  const Pose2D on_goal{1.0, 1.05, 0.0};  // inside the 0.1 m tolerance
  EXPECT_TRUE(controller.at_goal(on_goal));
  EXPECT_NEAR(*controller.angular_velocity(on_goal, 0.5), 0.0, kTolerance);

  const Pose2D short_of_goal{1.0, 0.5, 0.0};
  EXPECT_FALSE(controller.at_goal(short_of_goal));
}

TEST(PurePursuit, HandlesStandingExactlyOnTheTarget)
{
  PurePursuitConfig config = default_config();
  config.goal_tolerance = 0.0;
  PurePursuit controller{config};
  controller.set_path({{1.0, 1.0}});

  // Degenerate geometry: no arc exists, and the command must stay finite.
  const Pose2D on_target{1.0, 1.0, 0.0};
  EXPECT_NEAR(*controller.curvature(on_target), 0.0, kTolerance);
  EXPECT_NEAR(*controller.angular_velocity(on_target, 1.0), 0.0, kTolerance);
}

TEST(PurePursuit, ReportsNoCommandForNonFiniteGeometry)
{
  PurePursuit controller{default_config()};
  const double nan = std::numeric_limits<double>::quiet_NaN();

  // A localisation glitch or a planner bug can put NaN in the pose or the path.
  // A NaN steering rate compares false against every limit downstream, so the
  // controller has to report no command instead.
  controller.set_path({{nan, 0.0}});
  EXPECT_FALSE(controller.curvature(Pose2D{}).has_value());
  EXPECT_FALSE(controller.angular_velocity(Pose2D{}, 1.0).has_value());

  controller.set_path({{1.0, 1.0}});
  EXPECT_FALSE(controller.angular_velocity(Pose2D{nan, 0.0, 0.0}, 1.0).has_value());
  EXPECT_FALSE(controller.angular_velocity(Pose2D{}, nan).has_value());
}

TEST(PurePursuit, ReportsNoCommandWhenTheLimitItselfIsNotFinite)
{
  PurePursuitConfig config = default_config();
  config.max_angular = std::numeric_limits<double>::infinity();
  PurePursuit controller{config};
  controller.set_path({{0.0, 0.5}});  // a perfectly ordinary arc

  // The geometry is fine here; the configuration is not. Clamping against an
  // infinite bound would pass the raw curvature through to the wheels, so a
  // limit that is not a number has to be treated as no usable limit at all.
  EXPECT_FALSE(controller.angular_velocity(Pose2D{}, 1.0).has_value());
}

TEST(PurePursuit, SurvivesNonFinitePointsInThePath)
{
  PurePursuit controller{default_config()};
  const double nan = std::numeric_limits<double>::quiet_NaN();

  // A NaN distance compares false in both directions, which breaks the strict
  // weak ordering that min_element requires - the search would be undefined
  // rather than merely wrong.
  controller.set_path({{nan, 0.0}, {2.0, 0.0}, {nan, nan}, {0.5, 0.0}});

  EXPECT_TRUE(controller.lookahead_point(Pose2D{}).has_value());
  const auto command = controller.angular_velocity(Pose2D{}, 1.0);
  if (command.has_value()) {
    EXPECT_TRUE(std::isfinite(*command));
  }
}

TEST(PurePursuit, ReplacingThePathClearsTheOldOne)
{
  PurePursuit controller{default_config()};
  controller.set_path(straight_path());
  ASSERT_EQ(controller.path_size(), 5U);

  controller.set_path({});

  EXPECT_FALSE(controller.has_path());
  EXPECT_EQ(controller.path_size(), 0U);
  EXPECT_FALSE(controller.angular_velocity(Pose2D{}, 1.0).has_value());
}
