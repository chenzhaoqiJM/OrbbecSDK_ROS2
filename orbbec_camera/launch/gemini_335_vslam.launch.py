#!/usr/bin/env python3

# Copyright (c) 2026 Orbbec Inc.
# Licensed under the Apache License, Version 2.0.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    camera_name = LaunchConfiguration("camera_name")
    serial_number = LaunchConfiguration("serial_number")
    fps = LaunchConfiguration("fps")

    camera = Node(
        package="orbbec_camera",
        executable="orbbec_camera_node",
        namespace=camera_name,
        name="camera",
        output="screen",
        parameters=[
            {
                "camera_name": camera_name,
                "serial_number": serial_number,
                "connection_delay": 1,
                "enumerate_net_device": False,
                "enable_color": True,
                "color_width": 640,
                "color_height": 480,
                "color_fps": ParameterValue(fps, value_type=int),
                "color_format": "MJPG",
                "color_qos": "SENSOR_DATA",
                "color_camera_info_qos": "SENSOR_DATA",
                "enable_depth": True,
                "depth_width": 640,
                "depth_height": 480,
                "depth_fps": ParameterValue(fps, value_type=int),
                "depth_format": "Y16",
                "depth_qos": "SENSOR_DATA",
                "depth_camera_info_qos": "SENSOR_DATA",
                "depth_registration": True,
                "align_mode": "SW",
                "align_target_stream": "COLOR",
                "enable_frame_sync": True,
                "frame_aggregate_mode": "full_frame",
                "enable_point_cloud": False,
                "enable_colored_point_cloud": False,
                "enable_accel": True,
                "accel_rate": "200hz",
                "accel_range": "4g",
                "enable_gyro": True,
                "gyro_rate": "200hz",
                "gyro_range": "1000dps",
                "enable_sync_output_accel_gyro": True,
                "enable_sync_host_time": True,
                "time_domain": "global",
                "publish_tf": True,
                "tf_publish_rate": 0.0,
                "enable_publish_extrinsic": True,
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("camera_name", default_value="camera"),
            DeclareLaunchArgument("serial_number", default_value=""),
            DeclareLaunchArgument("fps", default_value="30"),
            camera,
        ]
    )
