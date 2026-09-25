# ABC GELLO 主臂硬件设置手册

> 适用环境：Linux x86_64 工作站（验证环境 Ubuntu 22.04）｜ 范围：ABC（arXiv:2606.27375）双臂遥操作站复刻的 GELLO 主臂硬件设置
> 路径约定：abc 仓 clone 至 `~/abc-teleop/abc`，本包放 `~/abc-teleop/hardware-setup/`（目录结构见同目录 README.md）。参考部署机 192.168.10.123，右臂已在其上完成配置。

## 硬件配置现状

右臂 GELLO 主臂 7 颗 XL330-M077-T 已按下表配置完毕；左臂、RealSense 相机、YAM 从臂及 USB-CAN 适配器尚未到位。

| 参数 | 出厂默认 | 当前配置 |
|---|---|---|
| ID | 1（全部相同） | 30–36（M0 底座 → M6 扳机，逐关节唯一） |
| 波特率 | 57600 | 4,000,000（baud_code 6） |
| 协议 | Protocol 2.0 | Protocol 2.0（未改动） |

ID 依据是 `~/abc-teleop/abc/deploy/robot/config.py` 中 `PROFILES["gtwy_config"]` 的 `leader_servo_ids=((20..26), (30..36))`：`_profile()` 内 `zip(("left","right"), ...)` 规定第一个 tuple 为左臂、第二个为右臂，tuple 内顺序即底座到末端的关节顺序。其它 profile 两臂同用默认 `(40..46)` 亦可——各臂有独立 U2D2 总线，ID 跨总线重复无冲突，实际约束只有"同一总线唯一 + 与自建 profile 一致"。

当前配置的 operational 含义：连接这条臂必须用 **4M 波特率**（57600 已扫不到），ID 扫描范围 30–36；4M 与 `latency_timer=1` 是 ABC 启动的硬性要求，出处为 `gello_leader.py:35` 的硬编码 `baudrate=4_000_000` 与同文件 `_verify_latency_timer` 检查。

U2D2（右臂）USB 序列号 `FTBIN9P6`，稳定路径 `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTBIN9P6-if00-port0`。建 profile 时用此 by-id 路径，不要写会漂移的 `/dev/ttyUSB*`。

## 工作站前置（新机器照此三条）

```
sudo usermod -aG dialout "$USER"   # 把当前用户加入 dialout；注销重登才生效，桌面会话有 linger 坑，见排查手册第 6 条
sudo cp ~/abc-teleop/hardware-setup/99-u2d2-latency.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger
pip3 install --user dynamixel-sdk
```

deploy 依赖用 `cd ~/abc-teleop/abc && uv sync --extra deploy` 安装（仅 Linux x86）；若踩 ruckig 源码构建失败，解法见排查手册第 7 条。Dynamixel Wizard 2.0 不常驻安装，需要 GUI（固件恢复、波形图诊断）时运行 `~/abc-teleop/hardware-setup/vendor/DynamixelWizard2Setup_x64-2.0.6 Linux`（ELF 安装器，文件名含空格）装一次即可，注意它与 CLI 脚本互斥占串口（第 5 条）。

## 排查手册（按踩坑顺序）

1. **USB 设备在 `lsusb`/`dmesg` 中完全无迹 = 第一层（电气/枚举）故障，与驱动和用户态软件无关。**USB 枚举不需要任何驱动，即使是不认识的设备也会出现。典型原因：U2D2 插在了另一台电脑上；仅充电线（有 5V 供电但无数据线，设备灯亮但系统无感知）。判据：插入时 `sudo dmesg -w` 无任何新事件。
2. **多颗出厂舵机同时上总线会造成"全静默"假象。**出厂舵机 ID 全为 1，广播 ping 时多颗同时应答、信号撞车成乱码，现象与"没有舵机"完全相同。配置必须单颗进行，或沿链每次只新加一颗（已配好的舵机不响应 ID 1 的点名）。
3. **U2D2 不向舵机供电。**舵机直插 U2D2 只有数据线没有电，永远不响应；必须经 U2D2 Power Hub Board + 5V 电源。舵机是否得电的判据：上电瞬间尾部红灯闪一下。
4. **U2D2 与 hub 上都有 TTL（3pin）和 RS485（4pin）两种口**，XL330 是 TTL 协议，接错口即全静默。
5. **Dynamixel Wizard 与命令行脚本互斥占用串口**（后者报 `Device or resource busy`），使用其中一方前先关闭/Disconnect 另一方。
6. **GUI 程序拿不到新加的用户组**：`systemd --user` 开机即启动且 `Linger=yes` 时，注销不会重启它，之后登录的桌面会话继承旧的组列表（缺 dialout），Wizard 打不开串口。修复：重启机器，或 `sudo loginctl terminate-user "$USER"`（会踢掉自己的全部会话）后重新登录。SSH 会话不受影响。
7. **`uv sync --extra deploy` 时 `ruckig==0.15.3` 源码构建失败**：ruckig 无 Linux x86 预编译 wheel 只能源码构建，其 pyproject 用的 `cmake.targets` 键已被 scikit-build-core ≥0.10 废弃（报 `Use build.targets instead of cmake.targets`），改用 0.9.x 后又缺 nanobind（CMake 报 `No module named nanobind`）。解法（不需改 pyproject）：
   ```
   uv pip install 'scikit-build-core<0.10' cmake ninja pybind11 nanobind
   uv pip install 'ruckig==0.15.3' --no-build-isolation
   uv sync --extra deploy   # 此时 ruckig 已就位，正常走完
   ```
   若机器访问 GitHub 超时：`astral.sh` 的 uv 安装脚本会卡死，改用 `pip3 install --user uv`；uv 自身下载 Python 也走 GitHub，加 `UV_PYTHON_DOWNLOADS=never` 让它用系统 Python 3.10（满足 requires-python >=3.10）。

## 接入新硬件

### 左臂（ID 20–26）

用 `scripts/` 三件套重复右臂流程：`dxl_scan.py` 发现出厂舵机（注意排查手册第 2 条，须单颗或沿链逐颗）→ `set_servo_ids.py` 逐颗设 ID + 4M → `verify_leader.py` 整臂只读上电验证。第二颗 U2D2 同样适用已装的 udev 规则，无需重复安装。

### RealSense 相机

序列号是出厂值，插上 USB3 直接读，填入 profile 的 `camera_serials`（顺序固定 top/left/right）：

```
python3 -c "import pyrealsense2 as rs; [print(d.get_info(rs.camera_info.serial_number), d.get_info(rs.camera_info.name)) for d in rs.context().devices]"
```

### YAM 从臂（CAN）

CAN 序列号同样是 USB-CAN 适配器的出厂值，读取：`udevadm info -a /sys/class/net/can0 | grep -m1 serial`。填入 profile 四槽 `can_l_lead/can_l_foll/can_r_lead/can_r_foll` 中的两个从臂槽（主臂槽留空，GELLO 不走 CAN），然后 `sudo -E env ROBOT_PROFILE=<profile名> bash ~/abc-teleop/abc/deploy/scripts/setup_can_names.sh` 生成固定接口名。

### 新站 profile 模板

在 `config.py` 的 `PROFILES` 字典追加一个条目即可；`_profile()` 封装了双臂三相机的全部共性，新站只给硬件差异：

```python
"mystation_config": _profile(
    camera_serials=("<top>", "<left>", "<right>"),          # 顺序固定 top/left/right
    leader_devices=(                                        # 第一个左臂、第二个右臂
        "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_<左臂U2D2序列号>-if00-port0",
        "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTBIN9P6-if00-port0",
    ),
    init_q=_DEFAULT_INIT_Q,
    can_serials=("", "<can_l_foll>", "", "<can_r_foll>"),   # 首尾主臂槽留空
    leader_servo_ids=((20, 21, 22, 23, 24, 25, 26), (30, 31, 32, 33, 34, 35, 36)),
),
```

留空字段的影响范围：`run_teleop.py` 走的 `teleop_specs` 只拉起 leader/follower 节点、不实例化相机（`specs.py` 中 `teleop_specs` 与 `camera_specs` 是两个独立函数），相机序列号留空不阻塞主臂；但 follower 节点依赖 `can_l_foll`/`can_r_foll` 固定接口名已生成，从臂未到位前不要跑 `run_teleop.py`，主臂侧验证一律用只读的 `verify_leader.py`。

### 首次遥操作

`run_teleop.py` 首次启动前将主臂摆到标定位姿（全关节 0 位、扳机半开），编码器偏移自动对齐到最近 π/4 网格。主臂是被动力反馈设备：运行时舵机电流≈0、关节自由、纯当编码器，仅有软限位反向力矩和扳机 ≤0.03A 回弹两处小主动电流（`gello_leader.py:99-105`），手掰安全；真正出力的是 YAM 从臂。
