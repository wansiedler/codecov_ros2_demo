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

#ifndef NAV_UTILS__PURE_PURSUIT_HPP_
#define NAV_UTILS__PURE_PURSUIT_HPP_

#include <optional>
#include <vector>

namespace nav_utils
{

/// Point in the map frame, in metres.
struct Point2D
{
  double x{0.0};
  double y{0.0};
};

/// Robot pose in the map frame.
struct Pose2D
{
  double x{0.0};
  double y{0.0};
  double yaw{0.0};  ///< rad, counter-clockwise from the x axis
};

/// Tuning of the pursuit geometry.
struct PurePursuitConfig
{
  double lookahead{1.0};       ///< m, distance of the carrot ahead of the robot
  double max_angular{1.5};     ///< rad/s
  double goal_tolerance{0.1};  ///< m, distance at which the path counts as done
};

/// Classic pure pursuit: pick a point on the path one lookahead distance away
/// and steer along the arc that reaches it.
class PurePursuit
{
public:
  explicit PurePursuit(const PurePursuitConfig & config);

  /// Replaces the path to follow. An empty path disables the controller.
  void set_path(std::vector<Point2D> path);

  [[nodiscard]] bool has_path() const { return !path_.empty(); }

  /// Number of points in the current path.
  [[nodiscard]] std::size_t path_size() const { return path_.size(); }

  /// True once the robot is within the goal tolerance of the last point.
  [[nodiscard]] bool at_goal(const Pose2D & pose) const;

  /// The point the controller is steering at, or nothing without a path.
  [[nodiscard]] std::optional<Point2D> lookahead_point(const Pose2D & pose) const;

  /// Signed curvature of the arc towards the lookahead point, in 1/m.
  /// Positive curvature turns left. Nothing when there is no path.
  [[nodiscard]] std::optional<double> curvature(const Pose2D & pose) const;

  /// Angular velocity for the given linear velocity, clamped to max_angular.
  /// Nothing when there is no path; zero once the goal is reached.
  [[nodiscard]] std::optional<double> angular_velocity(
    const Pose2D & pose, double linear_velocity) const;

private:
  PurePursuitConfig config_;
  std::vector<Point2D> path_;
};

}  // namespace nav_utils

#endif  // NAV_UTILS__PURE_PURSUIT_HPP_
