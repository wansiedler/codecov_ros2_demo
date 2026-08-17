#include <chrono>
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
  VelocityLimiterNode()
  : Node("velocity_limiter"),
    limiter_(load_limits())
  {
    publisher_ = create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 10);
    subscription_ = create_subscription<geometry_msgs::msg::Twist>(
      "cmd_vel_raw", 10,
      [this](const geometry_msgs::msg::Twist::SharedPtr msg) {on_command(*msg);});
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
    const rclcpp::Time now = this->now();
    const double dt = last_stamp_.nanoseconds() == 0 ? 0.0 : (now - last_stamp_).seconds();
    last_stamp_ = now;

    const Twist2D limited = limiter_.limit({msg.linear.x, msg.angular.z}, dt);

    geometry_msgs::msg::Twist out;
    out.linear.x = limited.linear;
    out.angular.z = limited.angular;
    publisher_->publish(out);
  }

  VelocityLimiter limiter_;
  rclcpp::Time last_stamp_{0, 0, RCL_ROS_TIME};
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
