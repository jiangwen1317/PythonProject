@echo off
chcp 65001 >nul
REM 开发环境初始化（入职/新克隆必跑一次）—— AGENTS.md「提交前验证（最小约束）」的配套步骤。
REM 作用：1) 安装 pytest 门禁依赖；2) 启用受版本控制的 pre-commit 钩子（管理员直推 main 路径的机械兜底）；3) 核对启用结果。

cd /d "%~dp0"

echo [setup-dev] 1/3 安装测试门禁依赖（requirements-dev.txt）...
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [setup-dev] 依赖安装失败，请检查 Python 环境后重试。
    exit /b 1
)

echo [setup-dev] 2/3 启用本地 pre-commit 钩子（git config core.hooksPath .githooks）...
git config core.hooksPath .githooks
if errorlevel 1 (
    echo [setup-dev] 钩子启用失败，请确认当前目录是 git 仓库。
    exit /b 1
)

echo [setup-dev] 3/3 核对钩子启用状态...
for /f "delims=" %%i in ('git config core.hooksPath') do set HOOKS_PATH=%%i
if not "%HOOKS_PATH%"==".githooks" (
    echo [setup-dev] 核对失败：core.hooksPath 当前值为 "%HOOKS_PATH%"，预期 ".githooks"。
    exit /b 1
)
echo [setup-dev] 核对通过：core.hooksPath = .githooks
echo [setup-dev] 完成。此后每次 git commit 前会自动运行 python -m pytest，失败即阻止提交。
exit /b 0
