@echo off
chcp 65001 >nul
echo ==========================================
echo 基础竞品分析工具 - PyInstaller 打包脚本
echo ==========================================
echo.

:: 检查是否安装了 pyinstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 PyInstaller，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败，请手动安装: pip install pyinstaller
        pause
        exit /b 1
    )
)

echo [1/4] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
:: 注意：不删除 .spec 文件，因为我们需要使用它进行打包
echo       清理完成
echo.

echo [2/4] 开始打包...
echo       使用配置文件: Power_and_Performance.spec
echo.

pyinstaller Power_and_Performance.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo [3/4] 打包成功！
echo.

:: 复制依赖文件到 dist 目录
echo [4/4] 复制依赖文件...
if exist "dist\Power_and_Performance.exe" (
    :: 复制 7z 解压工具（用于运行时解压嵌套ZIP）
    if exist "7z.exe"  copy /y "7z.exe"  "dist\" >nul
    if exist "7z.dll"  copy /y "7z.dll"  "dist\" >nul
    echo       依赖文件复制完成
) else (
    echo [警告] 未找到生成的 exe 文件
)

echo.
echo ==========================================
echo 打包完成！
echo 输出文件: dist\Power_and_Performance.exe
echo ==========================================
pause
