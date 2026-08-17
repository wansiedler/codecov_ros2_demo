cmake_minimum_required(VERSION 3.16)
project(nav_utils)

if(NOT CMAKE_CXX_STANDARD)
  # C++23 as far as GCC 13 in the Jazzy image supports it: std::numbers and the
  # ranges algorithms are there, std::print and ranges::to are not (GCC 14).
  set(CMAKE_CXX_STANDARD 23)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wnon-virtual-dtor)
endif()

# Export compile_commands.json so clang-tidy and IDEs can analyse the package.
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Enabled by CI: -DCOVERAGE=ON makes gcc emit .gcno/.gcda used by lcov.
option(COVERAGE "Build with gcov instrumentation" OFF)
if(COVERAGE)
  add_compile_options(-O0 -g --coverage -fprofile-abs-path)
  add_link_options(--coverage)
endif()

# Runtime analysis: -DSANITIZE=address,undefined (or thread) instruments the
# binaries so the test run itself reports memory and UB errors.
set(SANITIZE "" CACHE STRING "Comma separated sanitizer list passed to -fsanitize")
if(SANITIZE)
  add_compile_options(-O1 -g -fno-omit-frame-pointer -fsanitize=${SANITIZE})
  add_link_options(-fsanitize=${SANITIZE})
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_library(nav_utils_core
  src/velocity_limiter.cpp
  src/battery_monitor.cpp
  src/safety_zone.cpp
  src/pure_pursuit.cpp
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

  ament_add_gtest(test_pure_pursuit test/test_pure_pursuit.cpp)
  target_link_libraries(test_pure_pursuit nav_utils_core)

  # Linters are registered as ctest tests, so `colcon test` runs style, licence
  # and static analysis checks next to the unit tests. Selected explicitly
  # instead of ament_lint_common, which would also run uncrustify and fight the
  # clang-format configuration in .clang-format.
  #
  # Looked up quietly on purpose: the coverage, sanitizer and CodeQL jobs build
  # the package without the linter packages installed, and a hard requirement
  # would break those builds instead of just skipping the style checks.
  find_package(ament_cmake_copyright QUIET)
  find_package(ament_cmake_cppcheck QUIET)
  find_package(ament_cmake_cpplint QUIET)
  find_package(ament_cmake_lint_cmake QUIET)
  find_package(ament_cmake_xmllint QUIET)

  if(ament_cmake_copyright_FOUND)
    ament_copyright()
  endif()
  if(ament_cmake_cppcheck_FOUND)
    ament_cppcheck(LANGUAGE c++)
  endif()
  if(ament_cmake_cpplint_FOUND)
    ament_cpplint(FILTERS -build/header_guard -build/include_order -whitespace/braces
      -whitespace/newline)
  endif()
  if(ament_cmake_lint_cmake_FOUND)
    ament_lint_cmake()
  endif()
  if(ament_cmake_xmllint_FOUND)
    ament_xmllint()
  endif()
endif()

ament_export_include_directories(include)
ament_export_libraries(nav_utils_core)
ament_package()
