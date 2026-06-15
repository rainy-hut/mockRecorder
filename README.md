# Hardware Mock Recorder

Python PySide6 桌面工具，用于通过 TCP 代理录制硬件组件服务与仪器仪表之间的交互码流，并在无硬件环境下从 SQLite 进行 Mock 回放。

## 功能范围

- 支持 `SOCKET_SCPI_LINE`、`SOCKET_RAW`、`VISA_SOCKET` 代理。
- 支持 `TEXT`、`HEX_TEXT`、`BINARY` 码流保存。
- 支持 `OFF`、`RECORD`、`REPLAY` 三种模式。
- SQLite 保存 profile、test item、instrument、interaction、stream frame。
- 回放优先按 `product_name + process_station + product_code + tu_name + instrument_alias + request_hash + call_index` 匹配，兼容旧的 `profile_name + test_item_code` 匹配。
- 支持 `FIRST`、`LAST`、`BY_CALL_INDEX`、`ROUND_ROBIN`、`RANDOM` 回放策略的数据库查询能力。
- GUI 支持运行模式选择、基础配置、仪器 IP 映射、代理启动停止、录制数据分页查询/新增/编辑/删除/导入/导出、日志查看。

## 场景上下文

实际录制/回放场景由以下字段确定：

```text
产品，例如 MM、HERT
工序工位，例如 FT1-MP1
编码，例如 03020001
测试项，例如测试项 A、测试项 B、测试项 C
```

测试项服务执行每个测试项前，应通知本工具当前测试项。默认通知端口为：

```text
127.0.0.1:16000
```

发送一行 JSON 即可：

```json
{"testItem":"测试项A"}
```

也可以同时更新完整场景：

```json
{"productName":"MM","processStation":"FT1-MP1","productCode":"03020001","testItem":"测试项A"}
```

工具收到通知后，后续代理录制和回放都会使用新的测试项。

## GUI 使用流程

1. 打开工具后直接进入工作台。
2. 在“基础配置”页按两块配置：
   - 测试场景配置：产品、工序工位、编码。
   - 仪器 IP 映射配置：组件服务访问地址到真实仪器地址。
3. 测试项通知服务地址在“运行控制”中只读显示，默认来自配置文件。
4. 在仪器映射中配置：
   - 代理 IP / 代理端口：组件服务连接的地址。
   - 真实仪器 IP / 真实仪器端口：工具转发到的真实硬件地址。
   - 支持启用/禁用和测试连接。
5. 回到“运行控制”页开始录制/回放或停止。
6. 在“数据查询”页使用“普通查询”或“SQL 查询”，并可新增、编辑、删除录制数据。

## 界面文案约定

- 内部字段 `tuName` 在界面中显示为“测试项”，通知接口推荐使用 `testItem`。
- `VISA_INSTR_RESERVED` 在界面中显示为“厂商/VISA专用（暂不代理）”。
- “组件服务到真实仪器映射”简化为“仪器 IP 映射”。

## VISA 支持说明

第一版支持 `VISA_SOCKET`，前提是原软件可以把 VISA 资源配置为类似：

```text
TCPIP0::127.0.0.1::15026::SOCKET
```

工具再将本地代理端口映射到真实硬件：

```text
127.0.0.1:15026 -> 192.168.1.20:5025
```

`VISA_INSTR_RESERVED` 仅作为配置占位。VXI-11、HiSLIP、`TCPIP::inst0::INSTR`、USB、GPIB、厂家 DLL 等不在第一版透明代理范围。请优先改用 `VISA_SOCKET` 或普通 socket 方式接入。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

首次启动会将 `config/default_config.json` 复制到用户数据目录：

- Windows: `%APPDATA%/HardwareMockRecorder/`
- macOS: `~/Library/Application Support/HardwareMockRecorder/`
- Linux: `$XDG_CONFIG_HOME/HardwareMockRecorder/` 或 `~/.config/HardwareMockRecorder/`

运行数据位于：

```text
HardwareMockRecorder/
├── config.json
├── recorder.db
├── logs/app.log
└── exports/
```

## 打包

Windows 下安装 PyInstaller 后运行：

```bat
build_pyinstaller.bat
```

产物：

```text
dist/HardwareMockRecorder/HardwareMockRecorder.exe
```

使用 Inno Setup 打开 `installer/hardware_mock_recorder.iss` 可生成安装包。
