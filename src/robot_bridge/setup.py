import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'robot_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # ติดตั้งโฟลเดอร์ launch ด้วย
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        # ติดตั้งโฟลเดอร์ config
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        # ติดตั้งโฟลเดอร์ maps
        (os.path.join('share', package_name, 'maps'), glob(os.path.join('maps', '*.[yp][ag][m]*'))),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@todo.todo',
    description='ROS2 node for bridging serial communication with STM32 and Arduino.',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'arduino_reader = robot_bridge.arduino_reader:main',
            'ultrasonic_converter = robot_bridge.ultrasonic_converter:main',
            'teleop_stm = robot_bridge.teleop_stm:main',
            # เอา mower_teleop_key เก่าออกเพราะลบทิ้งแล้ว
        ],
    },
)
