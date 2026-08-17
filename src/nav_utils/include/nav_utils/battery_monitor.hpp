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

#ifndef NAV_UTILS__BATTERY_MONITOR_HPP_
#define NAV_UTILS__BATTERY_MONITOR_HPP_

#include <string>

namespace nav_utils
{

/// Coarse battery health used by the navigation stack to decide whether the
/// robot may accept new jobs, must return to the dock, or must stop.
enum class BatteryState { Ok, Low, Critical };

/// Thresholds expressed as state of charge in percent.
struct BatteryThresholds
{
  double low_percent{25.0};
  double critical_percent{10.0};
};

/// Converts pack voltage into a state of charge and a coarse battery state.
class BatteryMonitor
{
public:
  BatteryMonitor(int cell_count, const BatteryThresholds & thresholds);

  /// Estimates the state of charge in percent from the measured pack voltage,
  /// using a linear approximation between 3.2 V and 4.2 V per cell.
  double percent_from_voltage(double pack_voltage) const;

  /// Feeds a new voltage measurement and returns the resulting state.
  BatteryState update(double pack_voltage);

  /// State produced by the last update().
  BatteryState state() const { return state_; }

  /// State of charge produced by the last update(), in percent.
  double percent() const { return percent_; }

  /// True while the robot should head back to the charging station.
  bool should_return_to_dock() const { return state_ != BatteryState::Ok; }

  /// Human readable form of @p state, for logs and diagnostics.
  static std::string to_string(BatteryState state);

private:
  int cell_count_;
  BatteryThresholds thresholds_;
  BatteryState state_{BatteryState::Ok};
  double percent_{100.0};
};

}  // namespace nav_utils

#endif  // NAV_UTILS__BATTERY_MONITOR_HPP_
