# Changelog

## [1.0.2](https://github.com/wansiedler/perfect_ros2_atomic_package/compare/nav_utils-v1.0.1...nav_utils-v1.0.2) (2026-09-09)


### Bug Fixes

* **dco:** exempt GitHub's bot commits from the sign-off check ([#78](https://github.com/wansiedler/perfect_ros2_atomic_package/issues/78)) ([ec92d0e](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/ec92d0e9fa90053b0462342caef4b9074c8de043))
* **dco:** exempt merge commits from the sign-off check ([#76](https://github.com/wansiedler/perfect_ros2_atomic_package/issues/76)) ([85fe5e6](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/85fe5e6cbe302cd29cecda28f0c8d2b48b512090))

## [1.0.1](https://github.com/wansiedler/perfect_ros2_atomic_package/compare/nav_utils-v1.0.0...nav_utils-v1.0.1) (2026-09-09)


### Bug Fixes

* **release:** let bloom find rosdep's cache, name the tarball after the version, rebuild by tag ([#63](https://github.com/wansiedler/perfect_ros2_atomic_package/issues/63)) ([ee6d81b](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/ee6d81bea12b6d68eef6e9b4529d7b4087b76e93))

## 1.0.0 (2026-09-09)


### Features

* **ci:** fuzz the controller and the battery monitor ([554b436](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/554b436735357b78451cc71a63fabefced6f9d90))
* **ci:** fuzz the controller and the battery monitor ([2ac201d](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/2ac201d66a53c0cf10e74ff3dc5a1c20c99d4b04))
* **nav_utils:** add a pure pursuit path follower ([8acf666](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/8acf666a88cb5d67c5f457632691edcef548b09b))
* **nav_utils:** add battery monitor ([1232bb3](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/1232bb3e66617afe40ea88ddb6f6434f67116727))
* **nav_utils:** add pure pursuit, coverage trend chart and result documentation ([1819e7a](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/1819e7a5ddab4c8f46d33157f58a16a71b3294c9))
* **nav_utils:** add velocity limiter with unit tests ([30ba8cd](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/30ba8cd6ed339aa82e84a5f70ac765aae4d4b6e8))
* **nav_utils:** scale velocity inside safety zones ([2da108c](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/2da108c4e7b02098b04379206df4398452b1cdaf))
* **nav_utils:** scale velocity inside safety zones ([35d27b7](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/35d27b79e324faab251491c9178ff1621e74fbed))
* **release:** drive release-please from a config file, bump package.xml with the version ([#57](https://github.com/wansiedler/perfect_ros2_atomic_package/issues/57)) ([cea9d66](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/cea9d66cb3c6eddfca57d918c64b52ace9da3347))
* run the build and the tests in a container ([#55](https://github.com/wansiedler/perfect_ros2_atomic_package/issues/55)) ([e9aaa2e](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/e9aaa2eca10c45dced0b59acd874ff1161caba25))
* test the node, build with both compilers, harden the flags ([5a6f4e6](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/5a6f4e66026cda1b0397f31bf8c693c710130331))
* test the node, build with both compilers, harden the flags ([1977237](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/197723734c1c8ac234229cfbee523dfac0c4078d))


### Bug Fixes

* **ci:** run the Sonar step under bash ([2a3adaf](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/2a3adaf8424aad155563f3b3355de8d8943991a9))
* **ci:** satisfy clang-tidy and repair the trivy and OSV jobs ([381a8f7](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/381a8f7fb5e94d4abf111ee6c9f17180847c681e))
* **ci:** show the memcheck findings in the job log ([cdb2149](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/cdb2149c8527851c3d9a45711cd74936d01ed035))
* close the SonarCloud findings on this pull request ([f23b6dd](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/f23b6dd2a310ccf7a8e51540f696af2a2ecc22a3))
* **fuzz:** copy only the sources the image builds ([346009d](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/346009db9c88a6cbbea956e358a5da79e1c9c8c9))
* **nav_utils:** apply the clang-tidy fixes that silently missed ([fe83137](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/fe83137427ae7af86d9f584f19f6d6d1f903a0f6))
* **pre-commit:** analyse the sources as C++23 ([51196e1](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/51196e1ec9e4e5aaa7fd88b55d9aa8ec1555638e))
* **pure_pursuit:** keep the lookahead search well defined with NaN input ([d5358e7](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/d5358e776971426ed1f1748f4893fa98894b6458))
* **test:** stop relying on the M_PI macros ([7d61066](https://github.com/wansiedler/perfect_ros2_atomic_package/commit/7d61066d712eb6583b9d95773c4d064fb0cecda4))
