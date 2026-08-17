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
//
// Pack voltage arrives from a BMS over CAN, so a garbled frame can hand the
// monitor anything at all. Whatever comes in, the reported percentage has to
// stay inside 0..100 - the charging logic and the fleet display both trust it.

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "nav_utils/battery_monitor.hpp"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t * data, size_t size)
{
  if (constexpr size_t kNeeded = (sizeof(double) * 3) + sizeof(int32_t); size < kNeeded) {
    return 0;
  }

  double low = 0.0;
  double critical = 0.0;
  double voltage = 0.0;
  int32_t cells = 0;

  size_t offset = 0;
  std::memcpy(&low, data + offset, sizeof(low));
  offset += sizeof(low);
  std::memcpy(&critical, data + offset, sizeof(critical));
  offset += sizeof(critical);
  std::memcpy(&voltage, data + offset, sizeof(voltage));
  offset += sizeof(voltage);
  std::memcpy(&cells, data + offset, sizeof(cells));

  nav_utils::BatteryThresholds thresholds;
  thresholds.low_percent = low;
  thresholds.critical_percent = critical;

  nav_utils::BatteryMonitor monitor{cells, thresholds};

  // Unconditional: a NaN percentage would slip through a plain range check,
  // because every comparison against NaN is false. Whatever voltage arrives,
  // the reported state of charge has to be a real number within 0..100.
  if (
    const double percent = monitor.percent_from_voltage(voltage);
    !std::isfinite(percent) || percent < 0.0 || percent > 100.0) {
    __builtin_trap();
  }

  monitor.update(voltage);
  static_cast<void>(nav_utils::BatteryMonitor::to_string(monitor.state()));
  static_cast<void>(monitor.should_return_to_dock());

  return 0;
}
