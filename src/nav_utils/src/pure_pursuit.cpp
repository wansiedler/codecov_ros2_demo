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

#include "nav_utils/pure_pursuit.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <optional>
#include <utility>
#include <vector>

namespace nav_utils
{

namespace
{

double distance(const Point2D & from, const Pose2D & to)
{
  const double dx = from.x - to.x;
  const double dy = from.y - to.y;
  return std::hypot(dx, dy);
}

/// Expresses @p point in the frame of @p pose, x forward and y to the left.
Point2D to_robot_frame(const Point2D & point, const Pose2D & pose)
{
  const double dx = point.x - pose.x;
  const double dy = point.y - pose.y;
  const double cos_yaw = std::cos(pose.yaw);
  const double sin_yaw = std::sin(pose.yaw);
  return Point2D{cos_yaw * dx + sin_yaw * dy, -sin_yaw * dx + cos_yaw * dy};
}

}  // namespace

PurePursuit::PurePursuit(const PurePursuitConfig & config)
: config_(config)
{
}

void PurePursuit::set_path(std::vector<Point2D> path)
{
  path_ = std::move(path);
}

bool PurePursuit::at_goal(const Pose2D & pose) const
{
  if (path_.empty()) {
    return false;
  }
  return distance(path_.back(), pose) <= config_.goal_tolerance;
}

std::optional<Point2D> PurePursuit::lookahead_point(const Pose2D & pose) const
{
  if (path_.empty()) {
    return std::nullopt;
  }

  // Start from the point closest to the robot, otherwise a pose near the end of
  // the path would match an early point that lies behind it and steer backwards.
  std::size_t closest = 0;
  double closest_distance = distance(path_.front(), pose);
  for (std::size_t i = 1; i < path_.size(); ++i) {
    const double candidate = distance(path_[i], pose);
    if (candidate < closest_distance) {
      closest_distance = candidate;
      closest = i;
    }
  }

  // From there, the first point at least one lookahead away; the goal itself
  // when the remaining path is shorter than that, so the robot drives it out.
  for (std::size_t i = closest; i < path_.size(); ++i) {
    if (distance(path_[i], pose) >= config_.lookahead) {
      return path_[i];
    }
  }
  return path_.back();
}

std::optional<double> PurePursuit::curvature(const Pose2D & pose) const
{
  const std::optional<Point2D> target = lookahead_point(pose);
  if (!target) {
    return std::nullopt;
  }

  const Point2D local = to_robot_frame(*target, pose);
  const double squared = (local.x * local.x) + (local.y * local.y);
  if (squared == 0.0) {
    return 0.0;  // standing on the target, no arc to follow
  }
  return 2.0 * local.y / squared;
}

std::optional<double> PurePursuit::angular_velocity(
  const Pose2D & pose, double linear_velocity) const
{
  const std::optional<double> arc = curvature(pose);
  if (!arc) {
    return std::nullopt;
  }
  if (at_goal(pose)) {
    return 0.0;
  }
  const double bound = std::abs(config_.max_angular);
  return std::clamp(*arc * linear_velocity, -bound, bound);
}

}  // namespace nav_utils
