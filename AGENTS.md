# Repository Guidelines

## 项目结构与模块组织

本项目是一个 Python PySide6 桌面工具，用于通过本地代理录制和回放硬件 TCP 交互。入口是 `main.py`，它会启动 `app/gui/main_window.py`。核心代码位于 `app/`：`gui/` 放置页面和控件，`proxy/` 处理 TCP 会话、回放、载荷编码和上下文控制，`recorder/` 管理录制事件，`db/` 封装 SQLite 访问，`config/` 加载用户配置，`utils/` 提供共享工具函数。默认配置位于 `config/default_config.json`；数据库 schema 位于 `app/db/schema.sql`；资源文件位于 `app/assets/`。测试位于 `tests/`，其中包含 `tests/e2e_proxy_check.py`。

## 构建、测试与开发命令

创建环境后安装依赖：

```bash
pip install -r requirements.txt
```

本地运行应用：

```bash
python main.py
```

运行测试套件：

```bash
pytest
```

迭代开发时运行单个测试模块：

```bash
pytest tests/test_replay_engine.py
```

安装 PyInstaller 后构建 Windows 发行包：

```bat
build_pyinstaller.bat
```

打包后的可执行文件会输出到 `dist/HardwareMockRecorder/`。

## 编码风格与命名约定

使用 Python 3 风格，采用 4 空格缩进；在能帮助说明数据结构时添加类型标注。遵循现有模式：结构化模型使用 dataclass，数据库访问放在小型 repository 方法中，重复字符串应优先使用 `app/constants.py` 中的常量。函数、方法和模块使用 snake_case；类名使用 PascalCase，例如 `RuntimeContext` 和 `ReplayEngine`。面向配置的 dataclass 中保留 camelCase 字段，因为它们需要映射到 JSON 键。

## 测试指南

测试使用 pytest。测试文件应命名为 `test_*.py`，测试函数应命名为 `test_*`。SQLite 相关测试优先使用 `tmp_path`，参考 `tests/test_repository.py`，避免触碰本地录制数据。修改回放匹配、载荷编码、命令归一化或 repository 行为时，应补充聚焦测试。涉及代理或 GUI 邻近逻辑的改动，应手动 smoke run `python main.py` 或运行 e2e 检查。

## 提交与 Pull Request 指南

当前提交历史较少，未强制统一提交规范。提交信息建议使用简洁的祈使句，例如 `Add replay context fallback test` 或 `Fix payload hex decoding`。Pull Request 应包含简短摘要、测试结果、相关 issue 链接（如适用），以及可见 GUI 变更的截图。配置、schema 或打包流程的影响需要明确说明。

## 安全与配置提示

不要提交生成的用户数据，例如 `recorder.db`、日志、导出文件、`build/` 或 `dist/`。真实仪器 IP 和环境相关端口应保存在本地配置中，不要写入源码。修改默认端口或 schema 字段时，请同时更新 `config/default_config.json` 和 README。
