# ClusterFuzzLite builds the fuzz targets inside the OSS-Fuzz base image, which
# ships clang with libFuzzer and the sanitizer runtimes.
FROM gcr.io/oss-fuzz-base/base-builder:v1

COPY . $SRC/codecov_ros2_demo
COPY .clusterfuzzlite/build.sh $SRC/build.sh
WORKDIR $SRC/codecov_ros2_demo
