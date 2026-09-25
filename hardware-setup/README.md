# hardware-setup — ABC GELLO 主臂硬件配置包

> 用途：Dynamixel XL330 舵机的总线发现、ID/波特率配置、整臂只读验证，以及 Linux 工作站的部署前置配置。
> **权威操作文档是 `HANDOVER.md`**（含硬件配置现状、工作站前置、排查手册 7 条、新硬件接入与 profile 模板）；本文件只做目录索引。

## 目录索引

```
hardware-setup/
├── HANDOVER.md               # 权威操作文档（接手先读这份）
├── 99-u2d2-latency.rules     # udev 规则：FTDI latency_timer=1 持久化（ABC 启动检查硬性要求；安装命令见文件头注释）
├── scripts/                  # 纯 Python CLI 工具（依赖仅 pip install dynamixel-sdk，Linux/macOS 通用）
│   ├── dxl_scan.py           # 总线发现：7 档波特率 × ID 0–40 逐个点名；--broadcast 为快速广播模式
│   ├── set_servo_ids.py      # 逐颗设 ID + 4M 波特率，沿链增量配置，保证 ID 顺序 = 底座→扳机
│   └── verify_leader.py      # 整臂只读上电验证：ping 7 颗 + 流式打印关节角
└── vendor/                   # 第三方发布物存档，仅备份不执行，不入 git
    └── DynamixelWizard2Setup_x64-2.0.6   # Wizard 2.0 Linux 安装器（ELF，文件名含空格）；
        Linux                             #   固件恢复/波形图诊断需要 GUI 时运行它装一次即可
```
