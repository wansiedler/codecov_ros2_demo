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

#include <chrono>
#include <cstdint>
#include <memory>

#include "geometry_msgs/msg/twist.hpp"
#include "nav_utils/velocity_limiter.hpp"
#include "rclcpp/rclcpp.hpp"

namespace nav_utils
{

/// Subscribes to raw velocity commands, applies VelocityLimiter and republishes
/// the safe command on /cmd_vel.
class VelocityLimiterNode : public rclcpp::Node
{
public:
  VelocityLimiterNode() : Node("velocity_limiter"), limiter_(load_limits())
  {
    // cppcheck-suppress useInitializationList
    // The publisher can only be created once the Node base class is fully
    // constructed, so it cannot move into the initialiser list.
    publisher_ = create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 10);
    subscription_ = create_subscription<geometry_msgs::msg::Twist>(
      "cmd_vel_raw", 10, [this](const geometry_msgs::msg::Twist & msg) { on_command(msg); });
  }

private:
  VelocityLimits load_limits()
  {
    VelocityLimits limits;
    limits.max_linear = declare_parameter("max_linear", limits.max_linear);
    limits.max_angular = declare_parameter("max_angular", limits.max_angular);
    limits.max_linear_accel = declare_parameter("max_linear_accel", limits.max_linear_accel);
    return limits;
  }

  void on_command(const geometry_msgs::msg::Twist & msg)
  {
    // Nanoseconds rather than rclcpp::Time arithmetic: subtracting two Time
    // objects carries a clock-source check that can throw, and nothing here can
    // reach that case - both stamps come from this node's own clock. Doing the
    // arithmetic on the integer keeps the elapsed time obvious and the failure
    // modes finite.
    const int64_t now_nanos = this->now().nanoseconds();
    const double dt = last_nanos_ == 0 ? 0.0 : static_cast<double>(now_nanos - last_nanos_) * 1e-9;
    last_nanos_ = now_nanos;

    const Twist2D limited = limiter_.limit({msg.linear.x, msg.angular.z}, dt);

    geometry_msgs::msg::Twist out;
    out.linear.x = limited.linear;
    out.angular.z = limited.angular;
    publisher_->publish(out);
  }

  VelocityLimiter limiter_;
  int64_t last_nanos_{0};  ///< nanoseconds of the previous command, 0 before the first
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr subscription_;
};

}  // namespace nav_utils

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<nav_utils::VelocityLimiterNode>());
  rclcpp::shutdown();
  return 0;
}
