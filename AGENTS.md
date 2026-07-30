# AGENTS.md — 仓库导航与任务路由

本仓库是 7 个**互相独立**的 Python 小工具的集合，各目录之间**没有任何跨目录 import、不共享代码**（功能相似处均为各自独立实现，如多处各自复制了嵌套 ZIP 解压函数）。修改任一工具时只需关注其所在目录，不会影响其他目录。

空目录 `.qoder/rules/` 预留为后续项目规则（Rules）的落点，当前无需填充。

## 目录总览与任务路由

| 目录 | 一句话用途 | 主入口 | 运行命令 |
|---|---|---|---|
| `claudecode-analysis-engine/` | EMMC 测试日志解析入库（SQLite）与 RMA 报告导出 | `main.py`（CLI） | `python main.py --parse` 等 |
| `test_monitor/` | Playwright 自动巡检测试系统节点状态并推送告警 | `test_monitor.py`（CLI） | `python test_monitor.py --once` |
| `Package/` | 通用解压函数库（无入口，且当前无任何目录引用它） | 无（纯库） | 不可独立运行 |
| `竞品分析工具/` | 竞品数据汇总 + 竞品数据对比（tkinter 主菜单） | `main.py`（GUI） | `python main.py` |
| `基础竞品分析工具/` | 竞品功耗+性能汇总报表与功耗曲线，**CDM 数据汇总逻辑在此** | `Power_and_Performance.py`（GUI） | `python Power_and_Performance.py` |
| `竞品分析平滑度数据显示工具/` | 平滑度/性能数据提取与曲线展示（3 个独立脚本） | 各脚本独立入口（GUI） | `python <脚本名>.py` |
| `关键字数据汇总/` | 按 config.json 从 TXT 日志提取关键字写入 Excel 模板 | `keyword_extraction.py`（GUI） | `python keyword_extraction.py` |

**常见任务路由示例**：
- "修改 CDM 数据汇总逻辑" → `基础竞品分析工具/GET_Data.py` 的 `CDM_Speed_Collect` 函数（由 `Power_and_Performance.py` 主流程调用）。注意区分：`竞品分析平滑度数据显示工具/CDM_RandomRead.py` 只是 CDM 随机读数据的**展示**工具，不做汇总。
- "修改平滑度曲线（IDA/CLEAN Sheet）" → `基础竞品分析工具/GET_Data_HD_Tune.py`。
- "按 JSON 测试项配置汇总竞品日志 / 按 PN 码对比" → `竞品分析工具/`。
- "解析 RTMS 日志、查数据库、导 RMA 报告" → `claudecode-analysis-engine/`。

## 提交前验证（最小约束）

任何 git 提交前必须先在仓库根目录运行 `python -m pytest`（`pytest.ini` 已配置 testpaths：`claudecode-analysis-engine/tests`、`基础竞品分析工具/tests`、`关键字数据汇总/tests`、`竞品分析平滑度数据显示工具/tests`；`test_monitor` 已通过 norecursedirs 排除，因其 `test_monitor.py` 是运行时监控脚本，顶层导入 playwright/schedule/requests，被 pytest 收集会导致 ImportError 或副作用）。测试失败时**不得提交**，并如实报告失败输出。

该约定有配套的机械强制点：仓库内受版本控制的 `.githooks/pre-commit` 钩子脚本会在提交前自动运行 `python -m pytest`，失败即阻止提交。钩子默认不生效，需在每个克隆本地手动启用一次：

```
git config core.hooksPath .githooks
```

停用执行 `git config --unset core.hooksPath`；`git commit --no-verify` 可临时绕过（不推荐）。

---

## 1. claudecode-analysis-engine — EMMC 测试日志数据库分析系统

- **用途**：解析 EMMC 测试日志（RTMS 日志）入 SQLite（主表 `test_summary` + KV 指标表 `test_metrics` 双表模型），支持增量解析、Section 识别、定时监控（`.trigger` 信号文件触发）、RMA Excel 报告导出。
- **入口**：`main.py`（argparse CLI，非 GUI），按参数分派到解析/监控/导出/查询四种模式。
- **运行命令**：
  - 解析：`python main.py --parse`（可加 `--directory ./logs`、`--file xxx`、`--export`）
  - 监控：`python main.py --watch [--interval 分钟]`
  - 导出：`python main.py --export [--output x.xlsx]`
  - 查询：`--list-devices` / `--list-sections` / `--list-metrics [--section X]` / `--stat KEY` / `--show ID`
- **代码结构**：`main.py` → `src/`（`config.py` 配置、`database.py` 连接、`models.py` 模型、`parser.py` 解析引擎、`export.py` 导出、`query.py` 查询）；`src` 亦可作编程接口 import。
- **配置**：`config.json`（数据库路径、监控目录、扫描间隔）、`schema.sql`（建表）；依赖仅 openpyxl。详见目录内 `README.md`。

## 2. test_monitor — 分布式测试系统监控

- **用途**：用 Playwright 自动登录测试系统网页，检查指定任务/节点状态（FAIL/FATAL/ERROR），通过企业微信/钉钉 webhook 发送告警。
- **入口**：两个互不依赖的独立入口：
  - `test_monitor.py`（主入口）：按任务 ID 监控，含通知推送；`--once` 单次运行，默认每 60 分钟定时循环。
  - `node_monitor.py`：按节点名监控的变体，仅本地显示结果；支持 `--visible`（有头浏览器）、`--debug`。
- **运行命令**：`python test_monitor.py --once`（单次）或 `python test_monitor.py`（定时）；首次使用先运行 `setup.bat`（安装 requirements.txt 依赖 + `playwright install chromium`）。
- **配置**：`config.yaml`（系统 URL/账号、监控任务与节点列表、webhook）。详见目录内 `README.md`。

## 3. Package — 通用解压函数库

- **用途**：`zip.py` 仅提供 `unzip_all(folder, delete_after=True, max_rounds=5)` 一个函数，多轮递归解压目录下所有 .zip/.tar/.tar.gz/.tgz/.tar.bz2。
- **入口**：无 `__main__` 守卫，纯函数库，不可独立运行；`__init__.py` 为空。
- **现状**：全仓库无任何目录 import 该包（各工具目录均自带独立的解压实现）。

## 4. 竞品分析工具 — 竞品数据汇总与对比（GUI 主菜单）

- **用途**：竞品数据工具主菜单，两个功能：①竞品数据汇总（按 `json/` 下 20+ 个测试项 JSON 配置从日志提取关键字、分组百分比计算、写入模板 Excel）；②竞品数据对比（按 PN 码提取数据、填充对比模板、色阶/数据条条件格式）。
- **入口**：`main.py`（tkinter GUI），按钮分别调用同目录 `Data_Summarization.launch()` 与 `competitor_compare.launch()`（后者也可独立运行）。
- **运行命令**：`python main.py`；PyInstaller 打包配置为 `main.spec`。
- **配置/模板**：`json/` 测试项配置（CDM、Latency、RPMB、性能等）、`空模板.xlsx`、`comparison.xlsx`、`requirements.txt`。

## 5. 基础竞品分析工具 — 功耗+性能汇总报表（CDM 数据汇总所在地）

- **用途**：对竞品测试数据（CDM-CA、HD_Tune、H2 日志）做功耗与性能汇总，生成"竞品分析基本测试项.xlsx"报表，并用 matplotlib 生成功耗分析曲线 PNG 插入 Excel。
- **入口**：`Power_and_Performance.py`（tkinter 弹窗 GUI）。主流程：弹窗选目录/样品数 → 复制模板 → 统一解压嵌套 ZIP（运行时借助 `7z.exe`/`7z.dll`）→ `GET_Data.CDM_Speed_Collect`（**CDM 性能/功耗数据汇总**）→ 功耗曲线图表 → `GET_Data_HD_Tune.Speed_Collect`（平滑度曲线，IDA/CLEAN 两个 Sheet）。
- **模块关系**：`Power_and_Performance.py` import 同目录 `GET_Data.py` 与 `GET_Data_HD_Tune.py`；后两者各自带 `__main__` 守卫，可单独调试运行。
- **运行命令**：`python Power_and_Performance.py`；打包运行 `build.bat`（用 `Power_and_Performance.spec` 生成 `dist\Power_and_Performance.exe` 并复制 7z 工具）。
- **模板**：`竞品分析基本测试项模板.xlsx`。

## 6. 竞品分析平滑度数据显示工具 — 平滑度/性能曲线展示（3 个独立脚本）

- **用途**：从测试日志提取平滑度/性能数据，写入 Excel 模板并绘制曲线。三个脚本互不 import，各自独立运行：
  - `IO_BEKK_Smoothness.py`（PySimpleGUI）：提取 4 项读写速度指标（dwCurrentWriteMBps/dwCurrentReadMBps）写入 `IO_BEKK空模板.xlsx`。
  - `SQL_Smoothness.py`（PySimpleGUI）：处理 SQL 类测试（insert/updata/delect × burn/load 六项）写入 `SQL空模板.xlsx`。
  - `CDM_RandomRead.py`（PySimpleGUI，GUI 代码在模块顶层）：CDM 随机读数据交互式曲线展示（mplcursors）。
- **运行命令**：分别 `python IO_BEKK_Smoothness.py` / `python SQL_Smoothness.py` / `python CDM_RandomRead.py`；前两者有对应 `.spec` 打包配置，共用 `requirements.txt`。

## 7. 关键字数据汇总 — 日志关键字提取到 Excel

- **用途**：从 TXT 日志（含 ZIP 内日志）按关键字（如 `Max_Seq_Rd_Spd:`）提取值，支持"仅最后一次"或"提取全部匹配"两种模式，按 `config.json` 的 keyword→列映射写入 `template.xlsx`。
- **入口**：`keyword_extraction.py`（tkinter GUI，无 `__main__` 守卫，GUI 构建与 `mainloop()` 在模块顶层，直接运行即启动）。
- **运行命令**：`python keyword_extraction.py`；打包配置为 `1113-huizong.spec`。
- **配置**：`config.json` 定义 sheet_name 与各工具的 keyword→Excel 列映射；`template.xlsx` 为输出模板；两者默认从程序所在目录加载（兼容 PyInstaller frozen 模式），也可在 GUI 中手动指定。
