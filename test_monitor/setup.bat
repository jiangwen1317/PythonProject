@echo off
chcp 65001 >nul
echo 正在安装测试系统监控脚本依赖...

python -m pip install -r requirements.txt

echo.
echo 安装Playwright浏览器...
python -m playwright install chromium

echo.
echo 安装完成！
echo.
echo 请修改 config.yaml 配置文件：
echo   1. 设置测试系统URL、用户名、密码
echo   2. 配置要监控的任务和节点
echo   3. 设置企业微信或钉钉的webhook
echo.
echo 运行方式：
echo   1. 立即运行一次: python test_monitor.py --once
echo   2. 启动定时监控: python test_monitor.py
echo.
pause
