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

#include "nav_utils/battery_monitor.hpp"

#include <algorithm>
#include <string>

namespace nav_utils
{

namespace
{
constexpr double kEmptyCellVoltage = 3.2;
constexpr double kFullCellVoltage = 4.2;
}  // namespace

BatteryMonitor::BatteryMonitor(int cell_count, const BatteryThresholds & thresholds)
: cell_count_(std::max(1, cell_count)), thresholds_(thresholds)
{
}

double BatteryMonitor::percent_from_voltage(double pack_voltage) const
{
  const double cell_voltage = pack_voltage / static_cast<double>(cell_count_);
  const double span = kFullCellVoltage - kEmptyCellVoltage;
  const double ratio = (cell_voltage - kEmptyCellVoltage) / span;
  return std::clamp(ratio * 100.0, 0.0, 100.0);
}

BatteryState BatteryMonitor::update(double pack_voltage)
{
  percent_ = percent_from_voltage(pack_voltage);

  if (percent_ <= thresholds_.critical_percent) {
    state_ = BatteryState::Critical;
  } else if (percent_ <= thresholds_.low_percent) {
    state_ = BatteryState::Low;
  } else {
    state_ = BatteryState::Ok;
  }

  return state_;
}

std::string BatteryMonitor::to_string(BatteryState state)
{
  switch (state) {
    case BatteryState::Ok:
      return "OK";
    case BatteryState::Low:
      return "LOW";
    case BatteryState::Critical:
      return "CRITICAL";
  }
  return "UNKNOWN";
}

}  // namespace nav_utils
