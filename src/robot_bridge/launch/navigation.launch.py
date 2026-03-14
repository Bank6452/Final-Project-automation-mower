import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, LifecycleNode

def generate_launch_description():
    pkg_dir = get_package_share_directory('robot_bridge')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    nav2_params_path = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')
    map_yaml_file = os.path.join(pkg_dir, 'maps', 'empty_map.yaml')

    # ---- 1. Map Server (standalone, ไม่ผูกกับ AMCL) ----
    map_server_node = LifecycleNode(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        namespace='',          # <-- required in Humble
        output='screen',
        parameters=[{'yaml_filename': map_yaml_file, 'use_sim_time': False}]
    )

    # ---- 2. Lifecycle Manager สำหรับ map_server (activate ทันที) ----
    map_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[
            {'use_sim_time': False},
            {'autostart': True},
            {'node_names': ['map_server']}
        ]
    )

    # ---- 3. Nav2 Navigation Stack (ไม่รวม localization) ----
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'False',
            'params_file': nav2_params_path,
            'autostart': 'True',
        }.items()
    )

    return LaunchDescription([
        map_server_node,
        map_lifecycle_manager,
        nav2_launch,
    ])
