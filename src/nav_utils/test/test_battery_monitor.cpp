#include <gtest/gtest.h>

#include "nav_utils/battery_monitor.hpp"

using nav_utils::BatteryMonitor;
using nav_utils::BatteryState;
using nav_utils::BatteryThresholds;

namespace
{
// 12 cells: 38.4 V empty, 50.4 V full, 0.12 V per percent.
BatteryMonitor make_monitor()
{
  BatteryThresholds thresholds;
  thresholds.low_percent = 25.0;
  thresholds.critical_percent = 10.0;
  return BatteryMonitor(12, thresholds);
}
}  // namespace

TEST(BatteryMonitor, EstimatesPercentLinearlyBetweenCellBounds)
{
  const BatteryMonitor monitor = make_monitor();

  // Exact bounds are compared with a tolerance: the division by the cell count
  // introduces a rounding error far below any meaningful battery resolution.
  EXPECT_NEAR(monitor.percent_from_voltage(38.4), 0.0, 1e-9);
  EXPECT_NEAR(monitor.percent_from_voltage(50.4), 100.0, 1e-9);
  EXPECT_NEAR(monitor.percent_from_voltage(44.4), 50.0, 1e-9);
}

TEST(BatteryMonitor, ClampsPercentOutsideCellBounds)
{
  const BatteryMonitor monitor = make_monitor();

  EXPECT_DOUBLE_EQ(monitor.percent_from_voltage(30.0), 0.0);
  EXPECT_DOUBLE_EQ(monitor.percent_from_voltage(60.0), 100.0);
}

TEST(BatteryMonitor, ReportsOkAboveLowThreshold)
{
  BatteryMonitor monitor = make_monitor();

  EXPECT_EQ(monitor.update(48.0), BatteryState::Ok);
  EXPECT_FALSE(monitor.should_return_to_dock());
}

TEST(BatteryMonitor, ReportsLowBelowLowThreshold)
{
  BatteryMonitor monitor = make_monitor();

  EXPECT_EQ(monitor.update(41.0), BatteryState::Low);  // ~21.7 %
  EXPECT_TRUE(monitor.should_return_to_dock());
  EXPECT_NEAR(monitor.percent(), 21.67, 0.01);
}

TEST(BatteryMonitor, ReportsCriticalBelowCriticalThreshold)
{
  BatteryMonitor monitor = make_monitor();

  EXPECT_EQ(monitor.update(39.0), BatteryState::Critical);  // ~5 %
  EXPECT_EQ(monitor.update(38.4), BatteryState::Critical);  // empty
  EXPECT_TRUE(monitor.should_return_to_dock());
}

TEST(BatteryMonitor, RejectsNonPositiveCellCount)
{
  BatteryMonitor monitor(0, BatteryThresholds{});

  // A zero cell count would divide by zero; the constructor falls back to 1.
  EXPECT_DOUBLE_EQ(monitor.percent_from_voltage(4.2), 100.0);
}

TEST(BatteryMonitor, StringifiesEveryState)
{
  EXPECT_EQ(BatteryMonitor::to_string(BatteryState::Ok), "OK");
  EXPECT_EQ(BatteryMonitor::to_string(BatteryState::Low), "LOW");
  EXPECT_EQ(BatteryMonitor::to_string(BatteryState::Critical), "CRITICAL");
}
