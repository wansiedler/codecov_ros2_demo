cmake_minimum_required(VERSION 3.16)
project(nav_utils)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Enabled by CI: -DCOVERAGE=ON makes gcc emit .gcno/.gcda used by lcov.
option(COVERAGE "Build with gcov instrumentation" OFF)
if(COVERAGE)
  add_compile_options(-O0 -g --coverage -fprofile-abs-path)
  add_link_options(--coverage)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_library(nav_utils_core
  src/velocity_limiter.cpp
  src/battery_monitor.cpp
  src/safety_zone.cpp
)
target_include_directories(nav_utils_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

add_executable(velocity_limiter_node src/velocity_limiter_node.cpp)
target_link_libraries(velocity_limiter_node nav_utils_core)
ament_target_dependencies(velocity_limiter_node rclcpp geometry_msgs)

install(TARGETS nav_utils_core
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(TARGETS velocity_limiter_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)

  ament_add_gtest(test_velocity_limiter test/test_velocity_limiter.cpp)
  target_link_libraries(test_velocity_limiter nav_utils_core)

  ament_add_gtest(test_battery_monitor test/test_battery_monitor.cpp)
  target_link_libraries(test_battery_monitor nav_utils_core)

  ament_add_gtest(test_safety_zone test/test_safety_zone.cpp)
  target_link_libraries(test_safety_zone nav_utils_core)
endif()

ament_export_include_directories(include)
ament_export_libraries(nav_utils_core)
ament_package()
