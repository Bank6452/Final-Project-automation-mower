import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():

    # 1. นำเข้าโมเดล 3 มิติ และกระดูกหุ่นยนต์ (TF Tree) จากไฟล์เก่าที่คุณเคยทำไว้
    mower_desc_share = get_package_share_directory('mower_bot_description')
    xacro_file = os.path.join(mower_desc_share, 'urdf', 'robot.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file)
    robot_desc = robot_description_config.toxml()

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': False}]
    )

    # 2. ปลุกสมองคำนวณตำแหน่ง (EKF - robot_localization) พร้อมป้อนคัมภีร์ yaml
    robot_bridge_share = get_package_share_directory('robot_bridge')
    ekf_config_path = os.path.join(robot_bridge_share, 'config', 'ekf.yaml')

    ekf_local_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_odom',
        output='screen',
        parameters=[ekf_config_path, {'use_sim_time': False}]
    )

    ekf_global_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_map',
        output='screen',
        parameters=[ekf_config_path, {'use_sim_time': False}],
        remappings=[('odometry/filtered', 'odometry/global')]
    )

    navsat_transform_node = Node(
        package='robot_localization',
        executable='navsat_transform_node',
        name='navsat_transform_node',
        output='screen',
        parameters=[ekf_config_path, {'use_sim_time': False}],
        remappings=[('imu', '/camera/camera/imu'),  # RealSense IMU โดยตรง (teleop_stm ใหม่ไม่ publish /imu/data_raw แล้ว)
                    ('gps/fix', '/fix'),
                    ('odometry/filtered', 'odometry/global')]
    )

    rviz_config_file = os.path.join(mower_desc_share, 'config', 'view_bot.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file]
    )

    return LaunchDescription([
        # เปิดหน้าจอ 3 มิติ
        rviz_node,
        # เปิดกระดูกหุ่นยนต์
        robot_state_publisher_node,
        # วงใน (ล้อ + IMU)
        ekf_local_node,
        # วงนอก (ล้อ + IMU + GPS)
        ekf_global_node,
        # ตัวแปลงพิกัดดาวเทียมเป็น X,Y
        navsat_transform_node
    ])
