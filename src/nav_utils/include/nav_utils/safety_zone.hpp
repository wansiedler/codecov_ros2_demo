#ifndef NAV_UTILS__SAFETY_ZONE_HPP_
#define NAV_UTILS__SAFETY_ZONE_HPP_

namespace nav_utils
{

/// Zone the closest obstacle currently falls into.
enum class Zone
{
  Clear,     ///< nothing relevant in front of the robot
  Warning,   ///< slow down
  Danger,    ///< creep speed
  Stop       ///< full stop
};

/// Radii, in metres, delimiting the zones around the robot.
struct ZoneRadii
{
  double stop{0.3};
  double danger{0.8};
  double warning{1.5};
};

/// Maps the distance to the closest obstacle onto a speed scaling factor.
class SafetyZone
{
public:
  explicit SafetyZone(const ZoneRadii & radii);

  /// Zone the given obstacle distance falls into.
  Zone classify(double obstacle_distance) const;

  /// Speed scaling factor in [0, 1] for the given obstacle distance.
  double speed_scale(double obstacle_distance) const;

  /// Scales @p velocity down so it is safe for the given obstacle distance.
  double apply(double velocity, double obstacle_distance) const;

private:
  ZoneRadii radii_;
};

}  // namespace nav_utils

#endif  // NAV_UTILS__SAFETY_ZONE_HPP_
