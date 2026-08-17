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

# The fleet runs on Haswell or newer, so AVX2 and FMA are fair game. Guarded by
# the target architecture: -march is x86 only and would break an arm64 build.
# Override with -DARCH_BASELINE=x86-64-v2 for older hardware, or with an empty
# string to let the compiler pick its own default.
set(ARCH_BASELINE "haswell" CACHE STRING "Value passed to -march on x86_64")
if(ARCH_BASELINE AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64)$" AND
    (CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang"))
  add_compile_options(-march=${ARCH_BASELINE})
  message(STATUS "nav_utils: architecture baseline -march=${ARCH_BASELINE}")
endif()

# Warnings become errors in CI, where nobody reads them otherwise.
option(WARNINGS_AS_ERRORS "Turn compiler warnings into errors" OFF)
if(WARNINGS_AS_ERRORS)
  add_compile_options(-Werror)
endif()

# Hardening, following the OpenSSF Compiler Options Hardening Guide. Every flag
# is probed first: the set differs between GCC and clang and between targets,
# and an unsupported flag would otherwise fail the build.
option(HARDENING "Enable the recommended hardening flags" ON)
if(HARDENING AND (CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang"))
  include(CheckCXXCompilerFlag)

  set(candidate_flags
    -fstack-protector-strong
    -fstack-clash-protection
    -fcf-protection=full
    -fno-delete-null-pointer-checks
    -fno-strict-aliasing
  )
  foreach(flag IN LISTS candidate_flags)
    string(MAKE_C_IDENTIFIER "HAVE${flag}" flag_var)
    check_cxx_compiler_flag(${flag} ${flag_var})
    if(${flag_var})
      add_compile_options(${flag})
    endif()
  endforeach()

  # Bounds-checked std::vector::operator[] and friends. This is the one that
  # turns an out-of-range access into an abort instead of a wrong wheel command.
  add_compile_definitions(_GLIBCXX_ASSERTIONS)

  # _FORTIFY_SOURCE needs an optimising build; at -O0 it only emits a warning,
  # which -Werror would then turn into a failed coverage build.
  if(NOT CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_definitions(_FORTIFY_SOURCE=3)
  endif()

  add_link_options(-Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack)
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

# The fuzz targets are built by ClusterFuzzLite inside the OSS-Fuzz image; this
# option only exists so the same targets can be built locally with clang:
#   cmake -DFUZZING=ON -DCMAKE_CXX_COMPILER=clang++ ..
option(FUZZING "Build the libFuzzer targets" OFF)
if(FUZZING AND NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  message(FATAL_ERROR "FUZZING needs clang: -fsanitize=fuzzer is a clang feature")
endif()
if(FUZZING)
  # CONFIGURE_DEPENDS so a newly added target is picked up without re-running
  # cmake by hand.
  file(GLOB fuzz_sources CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/fuzz/fuzz_*.cpp)
  foreach(fuzz_source IN LISTS fuzz_sources)
    get_filename_component(fuzz_name ${fuzz_source} NAME_WE)
    add_executable(${fuzz_name} ${fuzz_source})
    target_link_libraries(${fuzz_name} nav_utils_core)
    target_compile_options(${fuzz_name} PRIVATE -fsanitize=fuzzer,address,undefined)
    target_link_options(${fuzz_name} PRIVATE -fsanitize=fuzzer,address,undefined)
  endforeach()
endif()

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

  # Integration test: launches the node and drives it over real topics, which is
  # the only way to cover the rclcpp wiring the unit tests cannot reach.
  find_package(launch_testing_ament_cmake QUIET)
  if(launch_testing_ament_cmake_FOUND)
    add_launch_test(test/test_velocity_limiter_node.py TIMEOUT 90)
  endif()

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
