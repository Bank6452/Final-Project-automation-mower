# ============================================================
#  Dockerfile สำหรับ mower_bot บน Raspberry Pi (ARM64)
#  ROS2 Humble | Ubuntu 22.04 | ไม่มี Gazebo (Hardware Only)
# ============================================================

FROM ros:humble-ros-base-jammy

# ---- ตัวแปรสภาพแวดล้อม ----
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV WORKSPACE=/ros2_ws

# ---- ติดตั้ง ROS2 dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ROS2 packages
    ros-humble-robot-state-publisher \
    ros-humble-xacro \
    ros-humble-robot-localization \
    ros-humble-nav2-bringup \
    ros-humble-nav2-map-server \
    ros-humble-nmea-navsat-driver \
    ros-humble-sensor-msgs \
    ros-humble-nav-msgs \
    ros-humble-std-msgs \
    ros-humble-geometry-msgs \
    ros-humble-tf2-ros \
    ros-humble-tf2-tools \
    ros-humble-joint-state-publisher \
    ros-humble-teleop-twist-keyboard \
    # RealSense D435i
    ros-humble-realsense2-camera \
    ros-humble-realsense2-description \
    # colcon build tools
    python3-colcon-common-extensions \
    python3-colcon-mixin \
    python3-rosdep \
    python3-vcstool \
    # Python deps
    python3-pip \
    python3-serial \
    # Utilities
    udev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- pip install เพิ่มเติม (ถ้าต้องการ) ----
RUN pip3 install --no-cache-dir pyserial

# ---- คัดลอก source code เข้า container ----
WORKDIR ${WORKSPACE}
COPY src/ ${WORKSPACE}/src/

# ---- build workspace ด้วย colcon ----
# หมายเหตุ: skip mower_bot_description ถ้าไม่ต้องการ Gazebo บน Pi
# ถ้าต้องการ localization.launch.py ก็ต้อง build mower_bot_description ด้วย (ใช้ URDF)
RUN /bin/bash -c " \
    source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build \
        --symlink-install \
        --cmake-args -DCMAKE_BUILD_TYPE=Release \
        --packages-select mower_bot_description robot_bridge \
    "

# ---- setup entrypoint ----
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
