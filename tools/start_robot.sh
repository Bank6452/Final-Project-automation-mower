#!/bin/bash

# --- Robot Master Startup Script ---

if [ ! -d "src/robot_bridge" ]; then
    echo "Error: กรุณารันสคริปต์นี้จากโฟลเดอร์ ~/ros2_ws เท่านั้น"
    exit 1
fi

echo "🛑 Stopping existing ROS2 nodes..."
killall -9 teleop_stm arduino_reader nmea_serial_driver 2>/dev/null
pkill -9 -f "realsense2_camera" 2>/dev/null
pkill -9 -f "rs_launch" 2>/dev/null
pkill -9 -f "robot_localization" 2>/dev/null
pkill -9 -f "nav2" 2>/dev/null
pkill -9 -f "rviz2" 2>/dev/null
pkill -9 -f "component_container" 2>/dev/null

ros2 daemon stop
ros2 daemon start

sleep 3

echo "🔨 Building Workspace..."
colcon build --packages-select robot_bridge

WS_DIR=$(pwd)
SOURCE_CMD="source /opt/ros/humble/setup.bash && source ${WS_DIR}/install/setup.bash"

echo "🚀 Opening 3 Tabs in a single terminal window..."

# เปิด 3 แท็บในหน้าต่างเดียว
# แต่ละแท็บ sleep รอให้ตัวก่อนหน้าเปิดขึ้นก่อน
# "exec bash" ที่ท้ายทำให้แท็บไม่ปิดตัวเองเมื่อคำสั่ง launch จบ
gnome-terminal --tab --title="1. HARDWARE" -- bash -c "$SOURCE_CMD && ros2 launch robot_bridge hardware_bringup.launch.py; exec bash"
sleep 8

# 2. Terminal สำหรับ Localization (EKF Fusion)
gnome-terminal --tab --title="2. LOCALIZATION" -- bash -c "$SOURCE_CMD && ros2 launch robot_bridge localization.launch.py; exec bash"
sleep 16

# 3. Terminal สำหรับ Navigation (Nav2 Stack)
gnome-terminal --tab --title="3. NAVIGATION" -- bash -c "$SOURCE_CMD && ros2 launch robot_bridge navigation.launch.py; exec bash"

echo ""
echo "✅ สคริปต์ทำงานสำเร็จ!"
echo "   📌 แท็บ 1 (HARDWARE)     → เริ่มทันที"
echo "   📌 แท็บ 2 (LOCALIZATION) → เริ่มหลัง 8 วินาที"
echo "   📌 แท็บ 3 (NAVIGATION)   → เริ่มหลัง 16 วินาที"
echo ""
echo "💡 ถ้าแท็บ 2 หรือ 3 ไม่ขึ้น ให้คลิกที่แท็บในหน้าต่าง Terminal"
