#!/bin/bash
# Sources the ROS underlay and, when the workspace has been built, its overlay,
# then runs whatever the caller asked for - an interactive shell by default,
# `make test` from the compose `test` service.
set -euo pipefail

# The ament setup scripts are not nounset-clean.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [ -f install/local_setup.bash ]; then
  # shellcheck disable=SC1091
  source install/local_setup.bash
fi
set -u

exec "$@"
