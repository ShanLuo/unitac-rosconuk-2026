#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    bringup_dir = get_package_share_directory(
        'unitac_bringup'
    )

    genforce_config = os.path.join(
        bringup_dir,
        'config',
        'genforce.yaml',
    )

    execute_motion = LaunchConfiguration(
        'execute_motion'
    )

    output_dir = LaunchConfiguration(
        'output_dir'
    )

    return LaunchDescription([

        DeclareLaunchArgument(
            'execute_motion',
            default_value='false',
            description=(
                'Enable physical MG400 execution. '
                'Default is false.'
            ),
        ),

        DeclareLaunchArgument(
            'output_dir',
            default_value='/ros2_ws/test_output/genforce_ros',
            description='Directory for collected GenForce data.',
        ),

        Node(
            package='unitac_collection',
            executable='genforce_collector',
            name='unitac_genforce_collector',
            output='screen',

            # Load validated experiment configuration first,
            # then allow these two launch arguments to override it.
            parameters=[
                genforce_config,
                {
                    'execute_motion': execute_motion,
                    'output_dir': output_dir,
                },
            ],
        ),
    ])