# ClusterFuzzLite builds the fuzz targets inside the OSS-Fuzz base image, which
# ships clang with libFuzzer and the sanitizer runtimes. That image builds as
# root by design - the tooling writes to $SRC and $OUT - and it compiles and
# exits rather than running as a service. NOSONAR
FROM gcr.io/oss-fuzz-base/base-builder:v1

# Only what the targets need. A recursive copy of the whole workspace would pull
# in .git and anything else lying around the checkout.
COPY src/nav_utils/include $SRC/codecov_ros2_demo/src/nav_utils/include
COPY src/nav_utils/src $SRC/codecov_ros2_demo/src/nav_utils/src
COPY src/nav_utils/fuzz $SRC/codecov_ros2_demo/src/nav_utils/fuzz
COPY .clusterfuzzlite/build.sh $SRC/build.sh

WORKDIR $SRC/codecov_ros2_demo
