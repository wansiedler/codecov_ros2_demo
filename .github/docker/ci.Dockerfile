# Prebuilt CI image for this workspace.
#
# Every job used to spend 150-340 s in "Set up the workspace" running the same
# apt-get and rosdep commands, against 13-21 s of actual compilation. Baking the
# toolchain and the package dependencies into one image moves that cost to a
# single build that only reruns when this file or package.xml changes.
#
# The tag follows the ROS distribution, so a future distro bump is a new tag
# rather than an edit to every workflow.
# Pinned by digest: the tag moves whenever the upstream image is rebuilt, and
# with it every dependency baked in below - silently, on a schedule nobody
# here controls. Dependabot proposes the new digest as a reviewable change.
FROM ros:jazzy-ros-base@sha256:da725acf8b0f9f30c683e33ffbdcd6482d077af96d6fdc7688c5f4f280b7d923

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# The manifest is copied before the install so that rosdep can resolve it in the
# same layer. Splitting the two would either leave the apt index in an earlier
# layer - where a later delete masks the bytes without removing them, costing
# ~100 MB - or repeat `apt-get update`. Editing package.xml therefore rebuilds
# the toolchain layer too, which is the cheaper trade: the manifest changes far
# less often than the sources, and the sources are not in the image at all.
COPY src/nav_utils/package.xml /tmp/deps/src/nav_utils/package.xml

# One layer: the union of what every job asks the ros-workspace action for, then
# the package dependencies rosdep resolves from the manifest, then the marker
# the action reads to skip the work it would otherwise repeat in every job.
# Without the marker the action behaves exactly as before, which keeps `act`
# runs against a plain ros:jazzy-ros-base image working.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ccache \
      clang \
      clang-format \
      clang-tidy \
      cmake \
      cppcheck \
      curl \
      git \
      graphviz \
      lcov \
      ninja-build \
      python3-colcon-common-extensions \
      python3-pip \
      ros-jazzy-ament-cmake-copyright \
      ros-jazzy-ament-cmake-cppcheck \
      ros-jazzy-ament-cmake-cpplint \
      ros-jazzy-ament-cmake-lint-cmake \
      ros-jazzy-ament-cmake-xmllint \
      unzip \
      valgrind \
 && rosdep update --rosdistro "$ROS_DISTRO" \
 && rosdep install --from-paths /tmp/deps/src --ignore-src -y \
 && touch /etc/ci-image.stamp \
 && rm -rf /tmp/deps /var/lib/apt/lists/*
