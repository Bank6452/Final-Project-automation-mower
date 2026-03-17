#!/bin/bash
# ============================================================
#  Docker Entrypoint — source ROS2 + workspace แล้ว exec CMD
# ============================================================

set -e

# Source ROS2 base
source /opt/ros/${ROS_DISTRO}/setup.bash

# Source workspace ถ้า build แล้ว
if [ -f "${WORKSPACE}/install/setup.bash" ]; then
    source "${WORKSPACE}/install/setup.bash"
fi

# รัน command ที่ส่งมา (default: bash)
exec "$@"
