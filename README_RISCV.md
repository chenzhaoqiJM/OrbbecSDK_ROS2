# 在 RISC-V 上运行 OrbbecSDK ROS 2

本仓库已在 RISC-V 64 位主机上使用 ROS 2 Humble 和 Gemini 335 相机完成构建与
验证。仓库已经包含原生 RISC-V 版 OrbbecSDK，克隆或复制整个仓库后可以直接构建，
不再依赖仓库外的 `/home/bianbu/OrbbecSDK_v2` 目录。

## 测试环境

- ROS 2：Humble
- 相机：Gemini 335，序列号 `CP0BB530004B`
- 固件版本：1.4.60
- OrbbecSDK / ROS 封装版本：2.9.3
- 连接方式：USB 2.1
- 内置原生 SDK：`orbbec_camera/SDK/lib/riscv64/`

## 依赖项

```bash
sudo apt-get install -y \
  libgflags-dev nlohmann-json3-dev libgoogle-glog-dev libdw-dev libssl-dev \
  mesa-utils libgl1 \
  ros-humble-image-transport ros-humble-image-transport-plugins \
  ros-humble-compressed-image-transport ros-humble-image-publisher \
  ros-humble-camera-info-manager ros-humble-diagnostic-updater \
  ros-humble-diagnostic-msgs ros-humble-statistics-msgs ros-humble-xacro \
  ros-humble-backward-ros ros-humble-camera-calibration-parsers \
  ros-humble-tf2-sensor-msgs ros-humble-cv-bridge
```

## 构建

```bash
source /opt/ros/humble/setup.bash
cd /home/bianbu/OrbbecSDK_ROS2
colcon build \
  --symlink-install \
  --parallel-workers 4 \
  --event-handlers console_direct+ \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release
```

RISC-V 动态库位于 `orbbec_camera/SDK/lib/riscv64/`，构建时会自动选择，并安装到
`install/orbbec_camera/lib/`。使用上面的 `--symlink-install` 时应分发整个仓库；如需
单独分发 `install` 目录，请去掉 `--symlink-install` 重新构建，普通安装产物会使用
相对 RPATH。如需临时使用其他 SDK 版本，仍可传入
`-DORBBEC_SDK_ROOT=/path/to/install`；该目录中必须包含 `include/libobsensor/` 和
`lib/libOrbbecSDK.so`。

## 运行 RGB-D / 视觉惯性 SLAM

```bash
source /opt/ros/humble/setup.bash
source /home/bianbu/OrbbecSDK_ROS2/install/setup.bash
ros2 launch orbbec_camera gemini_335_vslam.launch.py
```

通过验证的进程目前以临时用户单元 `orbbec-vslam.service` 运行。可使用以下命令
对其进行管理：

```bash
systemctl --user status orbbec-vslam.service
journalctl --user -u orbbec-vslam.service -f
systemctl --user stop orbbec-vslam.service
```

该启动文件会发布同步的 640x480 彩色图像和经软件对齐的深度图像，以及相机标定
数据、静态坐标变换和合并后的加速度计/陀螺仪数据。为节省 CPU 资源和 USB 带宽，
点云功能已禁用。可选参数包括 `camera_name`、`serial_number` 和 `fps`（默认值为
30）。

重要话题：

```text
/camera/color/image_raw
/camera/color/camera_info
/camera/depth/image_raw
/camera/depth/camera_info
/camera/gyro_accel/sample
/tf
/tf_static
```

已通过同时订阅多个话题的方式对相机进行了验证。启用软件对齐时，彩色图像与对齐后
的深度图像帧数相同，时间戳差值的中位数约为 1.03 ms，观测到的 DDS 订阅端速率约
为 17 Hz。SDK 后端接收两路视频流的速率均约为 30 Hz，软件对齐后的深度图像运行
速率约为 21 Hz，合并后的 IMU 数据运行速率约为 197–202 Hz。如需更高的吞吐量，
建议使用 USB 3 连接。

## RISC-V 限制

厂商的闭源库 `libob_frame_processor.so` 不支持 RISC-V。请勿在此目标平台上使用
硬件对齐：设备虽然会报告该模式，但无法构造其私有帧处理器。此启动配置特意选择了
SDK 的通用软件对齐路径，并避免传入需要上述缺失私有库的无关帧处理参数。

## 验证命令

```bash
source /opt/ros/humble/setup.bash
source /home/bianbu/OrbbecSDK_ROS2/install/setup.bash
ros2 run orbbec_camera list_devices_node
ros2 topic list
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
ros2 topic hz /camera/gyro_accel/sample
ros2 service call /camera/get_device_info orbbec_camera_msgs/srv/GetDeviceInfo '{}'
ros2 service call /camera/get_sdk_version orbbec_camera_msgs/srv/GetString '{}'
```

使用以下命令运行软件包测试：

```bash
curl -L http://download.ros.org/schema/package_format3.xsd \
  -o /tmp/package_format3.xsd
cat >/tmp/ros_package_catalog.xml <<'EOF'
<?xml version="1.0"?>
<catalog xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">
  <uri name="http://download.ros.org/schema/package_format3.xsd"
       uri="file:///tmp/package_format3.xsd"/>
</catalog>
EOF
XML_CATALOG_FILES=/tmp/ros_package_catalog.xml colcon test \
  --packages-select orbbec_camera orbbec_camera_msgs orbbec_description
colcon test-result --verbose
```

测试系统需要该目录文件，因为系统中的 `libxml2` 构建版本不包含 HTTP 加载器。
它仅改变代码检查期间查找 schema 的方式，运行时并不需要。
