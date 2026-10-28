# AGENTS.md — 仓库导航与任务路由

本仓库是 5 个**互相独立**的 Python 小工具的集合，各目录之间**没有任何跨目录 import、不共享代码**（功能相似处均为各自独立实现，如多处各自复制了嵌套 ZIP 解压函数）。修改任一工具时只需关注其所在目录，不会影响其他目录。

项目规则（Rules）统一放在 `.qoder/rules/` 目录，当前已包含 `commit-pytest-gate.md`（**提交类回合强制流程**，always_on 强制生效）；后续新增项目规则继续落在此目录。该规则是「提交前评估 → pytest 门禁 → 确认提交」这一重复流程的项目级持久承载，完整记录其触发条件（本回合将执行 `git commit`）、评估维度（提交粒度、敏感内容洁净性、门禁覆盖判断与免测路径手动验证、提交信息格式）与验证关口（pytest 摘要数字、提交前用户确认）。该流程**不依赖**用户级 auto-commit 技能：技能仅是便捷入口，缺失时按规则中的三步手动执行即为等效流程。

## 目录总览与任务路由

| 目录 | 一句话用途 | 主入口 | 运行命令 |
|---|---|---|---|
| `test_monitor/` | Playwright 自动巡检测试系统节点状态并推送告警 | `test_monitor.py`（CLI） | `python test_monitor.py --once` |
| `竞品分析工具/` | 竞品数据汇总 + 竞品数据对比（tkinter 主菜单） | `main.py`（GUI） | `python main.py` |
| `基础竞品分析工具/` | 竞品功耗+性能汇总报表与功耗曲线，**CDM 数据汇总逻辑在此** | `Power_and_Performance.py`（GUI） | `python Power_and_Performance.py` |
| `竞品分析平滑度数据显示工具/` | 平滑度/性能数据提取与曲线展示（3 个独立脚本） | 各脚本独立入口（GUI） | `python <脚本名>.py` |
| `关键字数据汇总/` | 按 config.json 从 TXT 日志提取关键字写入 Excel 模板 | `keyword_extraction.py`（GUI） | `python keyword_extraction.py` |

**常见任务路由示例**：
- "修改 CDM 数据汇总逻辑" → `基础竞品分析工具/GET_Data.py` 的 `CDM_Speed_Collect` 函数（由 `Power_and_Performance.py` 主流程调用）。注意区分：`竞品分析平滑度数据显示工具/CDM_RandomRead.py` 只是 CDM 随机读数据的**展示**工具，不做汇总。
- "修改平滑度曲线（IDA/CLEAN Sheet）" → `基础竞品分析工具/GET_Data_HD_Tune.py`。
- "按 JSON 测试项配置汇总竞品日志 / 按 PN 码对比" → `竞品分析工具/`。
- "解析 RTMS 日志、查数据库、导 RMA 报告" → 已迁出本仓库，由独立项目 `d:\Defective-Product-Analysis\database-analysis` 承接（原 `claudecode-analysis-engine/` 为初步设计，已删除）。

## 提交前验证（最小约束）

任何 git 提交前必须先在仓库根目录运行 `python -m pytest`。测试门禁的依赖声明在仓库根 `requirements-dev.txt`（testpaths 覆盖的核心模块均为纯标准库实现，pytest 是唯一第三方测试依赖），执行前先 `python -m pip install -r requirements-dev.txt`（收集范围以 `pytest.ini` 的 testpaths 为唯一事实源，即各工具目录下的 `tests/`，含 `test_monitor/tests`；`test_monitor` 根目录仍通过 norecursedirs 排除递归发现，因其 `test_monitor.py` 是运行时监控脚本，顶层导入 playwright/schedule/requests，被 pytest 收集会导致 ImportError 或副作用）。测试失败时**不得提交**，并如实报告失败输出。

**门禁覆盖边界（重要）**：pytest 门禁只验证从各工具抽离出来的**纯逻辑核心模块**（各工具目录下的 `*_core.py`，如 `data_core.py`、`extraction_core.py`、`config_core.py`、`cdm_core.py`、`monitor_core.py`；权威清单以 `pytest.ini` testpaths 实际收集到的测试为准）。其余源文件（各 GUI 入口如 `Power_and_Performance.py`/`main.py`/`keyword_extraction.py`、汇总主流程 `GET_Data.py`/`GET_Data_HD_Tune.py`/`Data_Summarization.py` 等）**不在机械检查范围内**。例外：`test_monitor/` 的两个监控脚本本体（`test_monitor.py`/`node_monitor.py`）有一层最小冒烟检查（`test_monitor/tests/test_scripts_smoke.py`，桩掉第三方依赖后只验证「可导入 + CLI 参数解析」，不触发浏览器/网络副作用），其 Playwright 页面交互与通知推送路径仍属免测范围。因此「pytest 通过」只代表核心纯函数行为与上述冒烟层未回归，**不代表** GUI 交互、Excel 写入、图表生成、页面自动化等主业务路径已验证；改动这些路径时仍需按各工具的运行命令手动验证。若在入口脚本中新增或发现可抽离的纯逻辑，优先抽入对应 `*_core.py` 并补最小单元测试；不为 GUI/绘图代码强行编写脆弱测试。

**免测路径验证入口（改动最热的平滑度主流程 GET_Data_HD_Tune.Speed_Collect 时优先使用）**：仓库内已提交一个可发现的 A/B 回归比对脚本 `基础竞品分析工具/tests/verify_mainflow.py`（不匹配 `test_*.py`，故不被 pytest 收集，仅供手动验证），随仓库分发一份最小 HD_Tune 样例 `基础竞品分析工具/tests/verify_data/`，可在任何克隆复现。它把基线版（默认 `HEAD`）与工作区版的 `Speed_Collect` 各跑一遍，比对中间产物 `Performance.csv`（逐字节）与 `平滑度曲线-IDA`/`平滑度曲线-CLEAN` 两个 Sheet 的全部非空单元格（比对复用 `data_core.diff_cell_maps` 纯逻辑）。运行命令（需装有 pandas/openpyxl/tkinter 的该工具运行环境，即 `python Power_and_Performance.py` 所用的解释器）：

```
python 基础竞品分析工具/tests/verify_mainflow.py            # 基线取 HEAD
python 基础竞品分析工具/tests/verify_mainflow.py --base HEAD~1  # 指定基线提交
```

预期比对结果：无回归时末行输出 `VERIFY-RESULT: PASS`、退出码 0，且两个 Sheet 的 `base=`/`worktree=` 单元格数相等且均非空（当前样例：IDA 21 格、CLEAN 11 格）；若行为发生回归，输出 `VERIFY-RESULT: FAIL`、退出码 2 并打印差异坐标。改动 `GET_Data_HD_Tune.py` 后应以此脚本的 PASS 记录作为一次有证据的手动比对，并将范围与量化结果（单元格数、PASS/FAIL）写入提交信息。CDM 汇总主流程 `GET_Data.CDM_Speed_Collect` 尚无专用验证入口，改动它须用 `python Power_and_Performance.py` 运行命令按真实样例手动验证性能/功耗 Sheet 写入后再提交。

该约定有配套的机械强制点：仓库内受版本控制的 `.githooks/pre-commit` 钩子脚本会在提交前自动运行 pytest，失败即阻止提交。钩子按以下顺序选择解释器：环境变量 `PRECOMMIT_PYTHON` 显式指定 → 仓库根 `.venv` 中装有 pytest 的解释器 → PATH 上装有 pytest 的 `python`/`py`；找不到装有 pytest 的解释器时会输出「环境错误（非测试失败）」的引导信息并以退出码 2 阻止提交（区别于测试失败的退出码）。

**钩子启用是入职/环境初始化的必做步骤**：每个新克隆在开始开发前，必须在仓库根目录运行一次环境初始化脚本 `setup-dev.bat`（安装 `requirements-dev.txt` 依赖 → 执行 `git config core.hooksPath .githooks` → 自动核对启用结果），或手动执行等效命令：

```
python -m pip install -r requirements-dev.txt
git config core.hooksPath .githooks
```

核对方式：运行 `git config core.hooksPath`，输出 `.githooks` 即为已启用；无输出即未启用，须补跑上述初始化步骤。停用执行 `git config --unset core.hooksPath`；`git commit --no-verify` 可临时绕过（不推荐）。

**本地 git 输出编码约定**：每个本地克隆还须执行一次 `git config core.quotepath false`（仅本地环境配置，不改仓库内容）。原因：本仓库大量目录为中文名（如 `基础竞品分析工具/`），git 默认会将非 ASCII 路径转义为八进制序列（`\346\...`），导致 `git log --numstat` 等输出无法被历史分析工具按目录正确聚合；关闭 quotepath 后中文路径在 git 输出中原样显示。核对方式：`git config core.quotepath` 输出 `false`，且 `git log --numstat` 中的中文路径不再出现八进制转义。

**Claude Code 本地权限白名单（2026-07 裁决：保留并对齐门禁）**：Claude Code 仍在本仓库使用，其本地配置 `.claude/settings.json`（被 `.gitignore` 忽略，不入库）的权限白名单须覆盖门禁命令的裸形式 `Bash(python -m pytest)`，与 `.qoder/rules/commit-pytest-gate.md` 要求的门禁命令保持一致；原有 `--collect-only`、`-v --tb=short` 等变体条目保留。若将来停用 Claude Code，删除该文件前须经用户显式确认。

**门禁三层强制状态（重要）**——三层机制的强制力各不相同，读者须清楚当前哪层是强制的、哪层需人工确认：

| 层级 | 载体 | 当前强制状态 |
|---|---|---|
| 本地钩子 | `.githooks/pre-commit` | **入职必做（初始化步骤强制）**：随仓库分发，git 机制上默认不生效，但已将启用固化为每个克隆的环境初始化必做步骤（运行仓库根 `setup-dev.bat`，脚本自动启用并核对）；核对方式为 `git config core.hooksPath` 输出 `.githooks`；`--no-verify` 仍可绕过（不推荐） |
| CI | `.github/workflows/pytest.yml` | **随克隆推送即生效**（push / PR 到 main 自动运行 pytest），但**不阻断合并**——检查失败只标红，不阻止 merge |
| 分支保护 | GitHub 仓库设置（Required status checks） | **已开启**（2026-07，经仓库管理员授权配置）：main 分支要求 `pytest` 检查通过才允许合并 PR，CI 失败机械阻断合并。当前配置：`enforce_admins=false`（管理员可直接 push main 或覆盖合并，日常直推工作流不受影响）、`strict=false`（不要求分支先同步到最新 main） |

结论：**走 PR 流程的合并已被机械阻断**——pytest 检查失败的 PR 无法合并进 main。管理员直推 main 的路径由本地钩子兜底：**最终决策（2026-07）**——在「(a) GitHub 侧 `enforce_admins=true` + 全面改走 PR」与「(b) 钩子启用固化为环境初始化必做步骤」之间选定 **(b)**，理由是保留日常直推工作流、且不依赖外部设置变更授权；(a) 保留为后续可升级项，若将来需要对管理员也做服务端强制，须经仓库管理员显式授权后在 GitHub 侧将 `enforce_admins` 设为 true（代价是所有改动必须走分支 + PR）。(b) 的机械兜底链条：`setup-dev.bat` 启用钩子 → 钩子在每次提交前强制运行 pytest → 失败即阻止提交；剩余缺口仅为 `--no-verify` 显式绕过与未跑初始化的克隆，均可用核对命令 `git config core.hooksPath` 一步检出。

---

## 1. test_monitor — 分布式测试系统监控

- **用途**：用 Playwright 自动登录测试系统网页，检查指定任务/节点状态（FAIL/FATAL/ERROR），通过企业微信/钉钉 webhook 发送告警。
- **入口**：两个互不依赖的独立入口（均 import 同目录 `monitor_core.py`，纯标准库模块，承载配置校验、错误状态判定、文本解析与告警消息拼装等纯逻辑，由 `test_monitor/tests/` 单元测试覆盖）：
  - `test_monitor.py`（主入口）：按任务 ID 监控，含通知推送；`--once` 单次运行，默认每 60 分钟定时循环。
  - `node_monitor.py`：按节点名监控的变体，仅本地显示结果；支持 `--visible`（有头浏览器）、`--debug`。
- **运行命令**：`python test_monitor.py --once`（单次）或 `python test_monitor.py`（定时）；首次使用先运行 `setup.bat`（安装 requirements.txt 依赖 + `playwright install chromium`）。
- **配置**：`config.yaml`（系统 URL/账号、监控任务与节点列表、webhook）。详见目录内 `README.md`。

## 2. 竞品分析工具 — 竞品数据汇总与对比（GUI 主菜单）

- **用途**：竞品数据工具主菜单，两个功能：①竞品数据汇总（按 `json/` 下 20+ 个测试项 JSON 配置从日志提取关键字、分组百分比计算、写入模板 Excel）；②竞品数据对比（按 PN 码提取数据、填充对比模板、色阶/数据条条件格式）。
- **入口**：`main.py`（tkinter GUI），按钮分别调用同目录 `Data_Summarization.launch()` 与 `competitor_compare.launch()`（后者也可独立运行）。
- **运行命令**：`python main.py`；PyInstaller 打包配置为 `main.spec`。
- **配置/模板**：`json/` 测试项配置（CDM、Latency、RPMB、性能等）、`空模板.xlsx`、`comparison.xlsx`、`requirements.txt`。

## 3. 基础竞品分析工具 — 功耗+性能汇总报表（CDM 数据汇总所在地）

- **用途**：对竞品测试数据（CDM-CA、HD_Tune、H2 日志）做功耗与性能汇总，生成"竞品分析基本测试项.xlsx"报表，并用 matplotlib 生成功耗分析曲线 PNG 插入 Excel。
- **入口**：`Power_and_Performance.py`（tkinter 弹窗 GUI）。主流程：弹窗选目录/样品数 → 复制模板 → 统一解压嵌套 ZIP（运行时借助 `7z.exe`/`7z.dll`）→ `GET_Data.CDM_Speed_Collect`（**CDM 性能/功耗数据汇总**）→ 功耗曲线图表 → `GET_Data_HD_Tune.Speed_Collect`（平滑度曲线，IDA/CLEAN 两个 Sheet）。
- **模块关系**：`Power_and_Performance.py` import 同目录 `GET_Data.py` 与 `GET_Data_HD_Tune.py`；后两者各自带 `__main__` 守卫，可单独调试运行。
- **运行命令**：`python Power_and_Performance.py`；打包运行 `build.bat`（用 `Power_and_Performance.spec` 生成 `dist\Power_and_Performance.exe` 并复制 7z 工具）。
- **模板**：`竞品分析基本测试项模板.xlsx`。

## 4. 竞品分析平滑度数据显示工具 — 平滑度/性能曲线展示（3 个独立脚本）

- **用途**：从测试日志提取平滑度/性能数据，写入 Excel 模板并绘制曲线。三个脚本互不 import，各自独立运行：
  - `IO_BEKK_Smoothness.py`（PySimpleGUI）：提取 4 项读写速度指标（dwCurrentWriteMBps/dwCurrentReadMBps）写入 `IO_BEKK空模板.xlsx`。
  - `SQL_Smoothness.py`（PySimpleGUI）：处理 SQL 类测试（insert/updata/delect × burn/load 六项）写入 `SQL空模板.xlsx`。
  - `CDM_RandomRead.py`（PySimpleGUI，GUI 代码在模块顶层）：CDM 随机读数据交互式曲线展示（mplcursors）。
- **运行命令**：分别 `python IO_BEKK_Smoothness.py` / `python SQL_Smoothness.py` / `python CDM_RandomRead.py`；前两者有对应 `.spec` 打包配置，共用 `requirements.txt`。

## 5. 关键字数据汇总 — 日志关键字提取到 Excel

- **用途**：从 TXT 日志（含 ZIP 内日志）按关键字（如 `Max_Seq_Rd_Spd:`）提取值，支持"仅最后一次"或"提取全部匹配"两种模式，按 `config.json` 的 keyword→列映射写入 `template.xlsx`。
- **入口**：`keyword_extraction.py`（tkinter GUI，无 `__main__` 守卫，GUI 构建与 `mainloop()` 在模块顶层，直接运行即启动）。
- **运行命令**：`python keyword_extraction.py`；打包配置为 `1113-huizong.spec`。
- **配置**：`config.json` 定义 sheet_name 与各工具的 keyword→Excel 列映射；`template.xlsx` 为输出模板；两者默认从程序所在目录加载（兼容 PyInstaller frozen 模式），也可在 GUI 中手动指定。
