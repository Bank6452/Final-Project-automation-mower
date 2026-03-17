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

# ถ้าไม่มี DISPLAY ให้เปิด Xvfb (virtual display) อัตโนมัติ
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:99
    Xvfb :99 -screen 0 1280x800x24 &
    sleep 1
fi

# รัน command ที่ส่งมา (default: bash)
exec "$@"
