# ClusterFuzzLite builds the fuzz targets inside the OSS-Fuzz base image, which
# ships clang with libFuzzer and the sanitizer runtimes. That image builds as
# root by design - the tooling writes to $SRC and $OUT - and it compiles and
# exits rather than running as a service. NOSONAR
# Pinned by digest, for the same reason as the CI image: v1 is a moving tag.
FROM gcr.io/oss-fuzz-base/base-builder:v1@sha256:8b4a73d83374b298a0a771eeec9a1d44ceff3416a678b7d7946303389d022aca

# Only what the targets need. A recursive copy of the whole workspace would pull
# in .git and anything else lying around the checkout.
COPY src/nav_utils/include $SRC/codecov_ros2_demo/src/nav_utils/include
COPY src/nav_utils/src $SRC/codecov_ros2_demo/src/nav_utils/src
COPY src/nav_utils/fuzz $SRC/codecov_ros2_demo/src/nav_utils/fuzz
COPY .clusterfuzzlite/build.sh $SRC/build.sh

WORKDIR $SRC/codecov_ros2_demo
