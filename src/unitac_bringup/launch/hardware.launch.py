#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    bringup_dir = get_package_share_directory(
        'unitac_bringup'
    )

    mg400_config = os.path.join(
        bringup_dir,
        'config',
        'mg400.yaml',
    )

    gelsight_config = os.path.join(
        bringup_dir,
        'config',
        'gelsight.yaml',
    )

    mg400_node = Node(
        package='unitac_mg400',
        executable='mg400_move_z_node',
        name='mg400_move_z_node',
        output='screen',
        parameters=[mg400_config],
    )

    gelsight_node = Node(
        package='unitac_gelsight',
        executable='gelsight_node',
        name='gelsight_node',
        output='screen',
        parameters=[gelsight_config],
    )

    return LaunchDescription([
        mg400_node,
        gelsight_node,
    ])