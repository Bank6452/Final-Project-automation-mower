import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Path to RealSense Launch
    realsense_launch_dir = get_package_share_directory('realsense2_camera')
    
    # Node 1: STM32 Teleop (สมองหลัก ส่งคำสั่ง C, E รับข้อมูล I, D)
    teleop_stm_node = Node(
        package='robot_bridge',
        executable='teleop_stm',
        name='teleop_stm',
        output='screen',
        parameters=[{
            'port': '/dev/stm32',
            'baudrate': 115200,
            'max_speed_ms': 1.25  # ความเร็วสูงสุดของรถจริง (m/s) - ปรับหลัง Calibrate
        }]
    )

    # Node 2: Arduino Reader (อ่าน Ultrasonic 3 ตัว)
    arduino_reader_node = Node(
        package='robot_bridge',
        executable='arduino_reader',
        name='arduino_reader',
        output='screen',
        parameters=[{
            'port': '/dev/ttyACM0',
            'baudrate': 115200
        }]
    )

    # Node 3: NMEA Navsat Driver (RTK GPS L29h)
    nmea_gps_node = Node(
        package='nmea_navsat_driver',
        executable='nmea_serial_driver',
        name='nmea_serial_driver',
        output='screen',
        parameters=[{
            'port': '/dev/gps_rtk', # ผูกชื่อพอร์ตตายตัวให้ GPS
            'baud': 115200
        }]
    )

    # Node 4: Ultrasonic to LaserScan Converter
    ultrasonic_converter_node = Node(
        package='robot_bridge',
        executable='ultrasonic_converter',
        name='ultrasonic_converter',
        output='screen'
    )

    # Node 5: RealSense Camera (D435i)
    realsense_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(realsense_launch_dir, 'launch', 'rs_launch.py')),
        launch_arguments={
            'enable_gyro': 'true',
            'enable_accel': 'true',
            'unite_imu_method': 'copy', 
            'enable_sync': 'true',
            'enable_color': 'true',     # กล้องปกติ
            'enable_depth': 'false',    # ปิด Depth เพื่อลดความร้อน (ยังไม่ใช้ตอนนี้)
            'pointcloud.enable': 'false', 
            'depth_module.profile': '640x480x15' # ลด Frame Rate ลงเพื่อช่วยเรื่องความร้อน
        }.items()
    )

    return LaunchDescription([
        teleop_stm_node,
        arduino_reader_node,
        ultrasonic_converter_node,
        nmea_gps_node,
        realsense_node
    ])
