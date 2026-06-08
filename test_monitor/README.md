# 测试系统监控脚本

自动监控分布式测试系统中指定任务的节点状态，发现错误时发送企业微信/钉钉通知。

## 功能特点

- 自动登录测试系统
- 定时检查指定任务的指定节点状态
- 识别 FAIL、FATAL、ERROR 等错误状态
- 支持企业微信和钉钉通知
- 可配置监控任务和节点
- 详细的日志记录

## 安装步骤

### 1. 安装依赖

双击运行 `setup.bat` 或手动执行：

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置脚本

编辑 `config.yaml` 文件：

```yaml
# 1. 设置测试系统信息
test_system:
  url: "http://your-test-system-url.com"
  username: "your_username"
  password: "your_password"

# 2. 配置要监控的任务和节点
monitor:
  tasks:
    - task_id: "297779"           # 从任务列表获取ID
      task_name: "任务名称"        # 用于显示
      nodes:                      # 要监控的节点名称列表
        - "DM3720.055.01"
        - "DM3720.055.02"

# 3. 配置通知方式（企业微信或钉钉）
wechat:
  enabled: true
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

### 3. 运行脚本

立即运行一次测试：
```bash
python test_monitor.py --once
```

启动定时监控（默认每60分钟检查一次）：
```bash
python test_monitor.py
```

## 配置说明

### 获取任务ID和节点名称

1. 打开测试系统的任务列表页面
2. 任务ID通常在URL中或任务列表的ID列
3. 节点名称在任务详情页的节点列表中

### 获取企业微信Webhook

1. 在企业微信群中添加群机器人
2. 复制Webhook地址中的key参数
3. 配置到 config.yaml 中

### 获取钉钉Webhook

1. 在钉钉群中添加群机器人
2. 复制Webhook地址
3. 如果启用了加签，还需要配置secret

## 定时运行（Windows）

使用任务计划程序每天运行：

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器为"每天"
4. 设置操作为"启动程序"
5. 程序路径选择 `python.exe`
6. 参数填写 `test_monitor.py --once`
7. 起始于填写脚本所在目录

## 注意事项

1. **页面元素选择器**：脚本中的CSS选择器（如 `input[type="text"]`）需要根据实际页面结构调整
2. **网络环境**：确保运行脚本的机器可以访问测试系统
3. **登录状态**：脚本每次运行会重新登录，不需要保持会话
4. **日志文件**：运行日志保存在 `monitor.log` 文件中

## 调试方法

如果脚本无法正常工作：

1. 修改 `test_monitor.py` 中的 `headless=True` 为 `headless=False`，查看浏览器操作过程
2. 使用浏览器开发者工具检查页面元素的选择器
3. 查看 `monitor.log` 日志文件排查问题
