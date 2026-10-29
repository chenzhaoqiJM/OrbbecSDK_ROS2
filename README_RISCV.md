# 在 K3（RISC-V）上运行 OrbbecSDK ROS 2

本仓库提供 K3（RISC-V 64 位）上的 ROS 2 Humble 相机使用说明，已经包含原生
RISC-V 版 OrbbecSDK，克隆或复制整个仓库后可以直接构建，无需额外的外部 SDK 目录。

## 运行环境

- ROS 2：Humble
- OrbbecSDK / ROS 封装版本：2.9.3
- 工作空间：`~/orbbec_ws`
- 源码目录：`~/orbbec_ws/OrbbecSDK_ROS2`
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

## 安装 USB 设备权限规则（udev）

首次在一台 Linux 主机上使用 USB 相机时，应安装仓库提供的 udev 规则，使普通用户
可以访问相机。该步骤属于系统配置，普通 `colcon build` 不会自动完成；更换主机或
更新规则文件后需要重新安装。

```bash
cd ~/orbbec_ws/OrbbecSDK_ROS2
sudo bash orbbec_camera/scripts/install_udev_rules.sh
```

脚本会将规则安装到 `/etc/udev/rules.d/99-obsensor-libusb.rules`，并执行规则重载和
`udevadm trigger`，无需再重复执行这两步。如果已经连接的相机仍出现权限错误，请
拔插一次相机。之后以普通用户运行 ROS 2 节点，不需要用 `sudo ros2 ...`。
USB 规则不负责网络相机的发现或网络连接配置。

## 构建

```bash
source /opt/ros/humble/setup.bash
cd ~/orbbec_ws
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

## 运行 RGB-D / IMU（供 SLAM 使用）

以下 launch 提供 SLAM 所需的相机输入，本身不启动 SLAM 算法。

```bash
source /opt/ros/humble/setup.bash
source ~/orbbec_ws/install/setup.bash
ros2 launch orbbec_camera gemini_335_vslam.launch.py
```

上述命令在前台运行，使用 `Ctrl+C` 停止。

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

## RISC-V 限制

当前随仓库分发的 RISC-V SDK 不包含厂商闭源库 `libob_frame_processor.so`。
Gemini 335 的硬件对齐路径会触发缺失的私有帧处理能力，因此本配置使用
`depth_registration=true`、`align_mode=SW` 和 `align_target_stream=COLOR`，并避免
显式传入需要该私有库的无关帧处理参数。启动日志可能报告缺少该库并使用透传处理。

`align_mode=SW` 控制图像对齐，`disparity_to_depth_mode=HW/SW` 控制视差转深度，
两者是不同功能。其他型号不能仅将对齐参数改成 `SW` 就认定适配完成；如果其深度
解码、视差转换或必要滤波本身依赖缺失的私有库，还需要 SDK 支持。

## 其他型号的 launch 适配范围

以下根据当前仓库 launch、SDK v2 官方支持表和扩展库说明列出适配候选范围，
实际支持情况需逐型号确认。
不能将存在 launch 文件或 udev 产品 ID 等同于已经支持 RISC-V。

| 型号 | 适配判断与现有入口 | 必须按型号处理的项目 |
| --- | --- | --- |
| Gemini 336、335L、336L；仓库列出的 Gemini 330、330L | 最优先验证；共用 `gemini_330_series.launch.py`，可参考 `gemini_335_vslam.launch.py` 的精简参数方式 | 先枚举 RGB/深度/IMU 能力及 profile；保留软件对齐和按需发布点云，不能假定所有型号都有相同的 640x480、MJPG、200 Hz 组合 |
| Gemini 335Lg、335Le | 同系列处理方式可参考，但连接适配须单独验证 | Lg 使用 GMSL 时还需 K3 解串器及内核驱动；Le 为以太网设备，须配置 IP/端口及网络发现，不能照搬 `enumerate_net_device=false` 的 USB 专用配置 |
| Gemini 345 / 345Lg、435Le、305 / 305g | 可评估独立的 K3 精简 launch；入口分别为 `gemini345*.launch.py`、`gemini435_le.launch.py`、`gemini_301_series.launch.py` | 保留各型号连接方式和 profile；305 系列现有配置是 848x530、彩色 YUYV，不能直接套用 335 的 MJPG 配置；IMU 按实际传感器启用 |
| Gemini 2、2 L、210、215 | 条件候选；入口为 `gemini2.launch.py`、`gemini2L.launch.py`、`gemini210.launch.py`（含 215） | 现有配置涉及软件视差转深度；必须验证 RISC-V 下该转换及深度处理路径。按设备枚举结果配置 IMU，现有配置多采用 100 Hz，不能照搬 200 Hz |
| Astra 2 | 条件候选；入口为 `astra2.launch.py` | 现有默认深度为 800x600、RLE，IMU 为 100 Hz；先验证 RLE 解码和私有处理依赖，再选 RGB-D 组合 |
| Femto Mega / Mega I | 条件候选；入口为 `femto_mega.launch.py` | 现有默认深度为 640x576、Y16，IMU 为 100 Hz；按连接方式和实际 profile 配置，验证深度处理及软件对齐路径 |
| Astra Mini Pro / Mini S Pro | 仅升级为 SDK v2 支持的 UVC 固件后评估；入口为 `astra.launch.py` | 官方最低 UVC 固件为 2.0.03；现有 launch 仍含 Y11 等旧配置，需按升级后的 profile 重新选格式并验证解码，不可据文件名认定已适配 |
| Femto Bolt | 当前不能归为仅修改 launch 即可完成的适配 | 官方说明其深度计算使用闭源 depthengine；官方分发目录没有 RISC-V 版本，本仓库也未包含该扩展。须先解决深度引擎依赖 |
| Gemini 2 XL、Astra+、Astra Pro Plus、仍使用 OpenNI 固件的旧设备 | 不能通过这份 SDK v2 的 launch 参数调整解决 | 前三者不在官方 SDK v2 支持范围内；旧协议设备需使用适用的 SDK/ROS 分支，或按厂商说明升级支持的型号 |

适配时建议新建独立的 `*_riscv.launch.py` 或共享 RISC-V 参数层，保留其他平台的
原有入口。Gemini 335 配置的关键是**精简实际传入节点的参数**，而不是把原 launch
的所有滤波开关都传入并设为 `false`：驱动会根据参数是否被显式提供来决定是否调用
SDK 的属性/滤波接口，传入 `false` 也可能触发不支持的接口。

逐型号验证流程：

1. 停止其他占用相机的进程，先运行下面的设备及 profile 枚举命令。
2. 先只开启原生深度和彩色流，关闭点云和 IMU，确认实际收到帧。只设置启动所需的
   参数；若必要的解码或深度计算依赖缺失的扩展，先解决 SDK 依赖。
3. 再启用软件对齐、帧同步和 `full_frame` 聚合，检查两路图像尺寸、光学坐标系、
   CameraInfo 内参以及时间戳；按实际 profile 降低分辨率/帧率。
4. 有加速度计和陀螺仪时，再启用 IMU，选择两者均支持的速率、量程，并验证合并
   输出。无 IMU 时，三个开关 `enable_accel`、`enable_gyro`、
   `enable_sync_output_accel_gyro` 都应关闭；合并开关会自动启用两种传感器。
5. 最后同时订阅所需话题测试吞吐量，再将该型号标记为 K3 已验证。

参考资料：

- [官方 SDK v2 设备/固件支持表](https://github.com/orbbec/OrbbecSDK_v2#14-supported-devices)
- [官方闭源扩展说明](https://github.com/orbbec/OrbbecSDK_v2/tree/main/extensions)
- [depthengine 已分发的平台](https://github.com/orbbec/OrbbecSDK_v2/tree/main/extensions/depthengine)
- 本仓库的 [ROS 2 支持型号及 launch 对照](README.MD#supported-devices)

## 验证命令

```bash
source /opt/ros/humble/setup.bash
source ~/orbbec_ws/install/setup.bash
ros2 run orbbec_camera list_devices_node
ros2 run orbbec_camera list_camera_profile_mode_node
```

枚举命令用于启动相机节点之前；有多台相机时，profile 工具可追加
`--serial_number YOUR_SERIAL_NUMBER`（替换为目标相机序列号）。
启动相机后，在另一个已经加载上述环境的终端执行：

```bash
ros2 topic list
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
ros2 topic hz /camera/gyro_accel/sample
ros2 service call /camera/get_device_info orbbec_camera_msgs/srv/GetDeviceInfo '{}'
ros2 service call /camera/get_sdk_version orbbec_camera_msgs/srv/GetString '{}'
```

使用以下命令运行软件包测试：

```bash
cd ~/orbbec_ws
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
