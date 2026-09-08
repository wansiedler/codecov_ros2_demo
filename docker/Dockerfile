# Development image: the CI image plus a user.
#
# The CI image (.github/docker/ci.Dockerfile, published by ci-image.yml) carries
# the toolchain, lcov, valgrind, the sanitizer-capable compilers and every
# dependency rosdep resolves from package.xml. Deriving from it rather than
# repeating the list is what keeps "it passes in the container" and "it passes
# in CI" the same statement. What is added here is only what an interactive
# session needs and a CI job does not: a user with the host's UID so the
# bind-mounted checkout stays writable on both sides, sudo, a debugger, and an
# entrypoint that sources ROS.
#
# BASE is overridable for a machine without registry access: build the CI image
# locally and point at it -
#   docker build -f .github/docker/ci.Dockerfile -t local/ci:jazzy .
#   BASE=local/ci:jazzy docker compose build
ARG BASE=ghcr.io/wansiedler/perfect_ros2_atomic_package/ci:jazzy
# hadolint ignore=DL3006
FROM ${BASE}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER_NAME=dev
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    CCACHE_DIR=/home/${USER_NAME}/.ccache \
    ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash-completion \
      gdb \
      sudo \
 && rm -rf /var/lib/apt/lists/*

# The ros images already ship a user at UID 1000 (`ubuntu` on noble); take the
# id over rather than fail on it, the way the Navflex base images do, so the
# files colcon writes into the bind mount belong to the person on the host.
# getent exits 2 when the id is free; under pipefail that must not end the RUN.
RUN existing=$(getent passwd "${USER_ID}" | cut -d: -f1 || true) \
 && if [ -n "$existing" ] && [ "$existing" != "${USER_NAME}" ]; then \
      usermod -l "${USER_NAME}" -d "/home/${USER_NAME}" -m "$existing"; \
    elif [ -z "$existing" ]; then \
      useradd --no-user-group --create-home --uid "${USER_ID}" --shell /bin/bash "${USER_NAME}"; \
    fi \
 && existing_group=$(getent group "${GROUP_ID}" | cut -d: -f1 || true) \
 && if [ -n "$existing_group" ] && [ "$existing_group" != "${USER_NAME}" ]; then \
      groupmod -n "${USER_NAME}" "$existing_group"; \
    elif [ -z "$existing_group" ]; then \
      groupadd -g "${GROUP_ID}" "${USER_NAME}"; \
    fi \
 && usermod -g "${GROUP_ID}" "${USER_NAME}" \
 && echo "${USER_NAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USER_NAME}" \
 && chmod 0440 "/etc/sudoers.d/${USER_NAME}" \
 && mkdir -p "/home/${USER_NAME}/ws" "/home/${USER_NAME}/.ccache" \
 && chown -R "${USER_ID}:${GROUP_ID}" "/home/${USER_NAME}"

COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh

# Numeric, so the id resolves even when USER_NAME was renamed onto an existing
# account (hadolint DL3002 / DL3066).
USER ${USER_ID}
WORKDIR /home/${USER_NAME}/ws

# Liveness for tools that insist on one: the ROS underlay is there.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["bash", "-c", "test -f /opt/ros/jazzy/setup.bash"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
