#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式测试系统监控脚本
用于自动检查指定任务的节点状态，发现错误时发送通知
"""

import yaml
import json
import time
import logging
import requests
import schedule
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Page, Browser


@dataclass
class NodeStatus:
    """节点状态数据类"""
    name: str
    status: str
    project: str
    ip: str
    details: Optional[str] = None


@dataclass
class TaskConfig:
    """任务配置数据类"""
    task_id: str
    task_name: str
    nodes: List[str]


class NotificationSender:
    """通知发送器"""

    def __init__(self, config: Dict):
        self.config = config

    def send_wechat(self, message: str) -> bool:
        """发送企业微信通知"""
        if not self.config.get('wechat', {}).get('enabled'):
            return False

        webhook_url = self.config['wechat']['webhook_url']
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }

        try:
            response = requests.post(
                webhook_url,
                json=data,
                timeout=10
            )
            result = response.json()
            if result.get('errcode') == 0:
                logging.info("企业微信通知发送成功")
                return True
            else:
                logging.error(f"企业微信通知发送失败: {result}")
                return False
        except Exception as e:
            logging.error(f"企业微信通知发送异常: {e}")
            return False

    def send_dingtalk(self, message: str) -> bool:
        """发送钉钉通知"""
        if not self.config.get('dingtalk', {}).get('enabled'):
            return False

        webhook_url = self.config['dingtalk']['webhook_url']
        secret = self.config['dingtalk'].get('secret')

        # 如果需要加签
        if secret:
            import base64
            import hashlib
            import hmac
            import urllib.parse

            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }

        try:
            response = requests.post(
                webhook_url,
                json=data,
                timeout=10
            )
            result = response.json()
            if result.get('errcode') == 0:
                logging.info("钉钉通知发送成功")
                return True
            else:
                logging.error(f"钉钉通知发送失败: {result}")
                return False
        except Exception as e:
            logging.error(f"钉钉通知发送异常: {e}")
            return False

    def send(self, message: str):
        """发送所有启用的通知"""
        self.send_wechat(message)
        self.send_dingtalk(message)


class TestSystemMonitor:
    """测试系统监控器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.notification = NotificationSender(self.config)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._setup_logging()

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('log', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'monitor.log')

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def _init_browser(self):
        """初始化浏览器"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(
            headless=True,  # 无头模式
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = self.browser.new_page()
        self.page.set_viewport_size({'width': 1920, 'height': 1080})

    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None

    def login(self) -> bool:
        """登录测试系统"""
        try:
            test_system = self.config['test_system']
            url = test_system['url']
            username = test_system['username']
            password = test_system['password']

            logging.info(f"正在登录测试系统: {url}")
            self.page.goto(url, wait_until='networkidle')

            # 等待登录表单加载
            # 注意：这里需要根据实际页面结构调整选择器
            self.page.wait_for_selector('input[type="text"]', timeout=10000)

            # 填写登录信息
            self.page.fill('input[type="text"]', username)
            self.page.fill('input[type="password"]', password)

            # 点击登录按钮
            self.page.click('button[type="submit"]')

            # 等待登录成功（等待任务列表或特定元素出现）
            self.page.wait_for_selector('.task-list, .node-list', timeout=10000)

            logging.info("登录成功")
            return True

        except Exception as e:
            logging.error(f"登录失败: {e}")
            return False

    def get_task_nodes(self, task_id: str) -> List[NodeStatus]:
        """获取任务的节点列表"""
        nodes = []
        try:
            # 导航到任务详情页
            # 注意：这里需要根据实际URL结构调整
            task_url = f"{self.config['test_system']['url']}/task/{task_id}"
            self.page.goto(task_url, wait_until='networkidle')

            # 等待节点列表加载
            self.page.wait_for_selector('table tbody tr', timeout=10000)

            # 获取所有节点行
            rows = self.page.query_selector_all('table tbody tr')

            for row in rows:
                try:
                    # 提取节点信息
                    # 注意：这里需要根据实际页面结构调整选择器
                    cells = row.query_selector_all('td')
                    if len(cells) >= 8:
                        node_name = cells[2].inner_text().strip()  # 节点名称
                        project = cells[6].inner_text().strip()    # 项目
                        status = cells[7].inner_text().strip()     # 状态
                        ip = cells[8].inner_text().strip() if len(cells) > 8 else ""  # IP

                        nodes.append(NodeStatus(
                            name=node_name,
                            status=status,
                            project=project,
                            ip=ip
                        ))
                except Exception as e:
                    logging.warning(f"解析节点行失败: {e}")
                    continue

        except Exception as e:
            logging.error(f"获取任务节点失败: {e}")

        return nodes

    def get_node_details(self, node_name: str) -> str:
        """获取节点详情（测试步骤状态）"""
        try:
            # 点击节点进入详情
            node_link = self.page.query_selector(f'text={node_name}')
            if node_link:
                node_link.click()
                self.page.wait_for_timeout(2000)  # 等待页面加载

                # 获取错误信息
                error_elements = self.page.query_selector_all('.error, .fail, .fatal')
                errors = [el.inner_text().strip() for el in error_elements]

                return "; ".join(errors) if errors else ""

        except Exception as e:
            logging.error(f"获取节点详情失败: {e}")

        return ""

    def check_task(self, task_config: TaskConfig) -> List[NodeStatus]:
        """检查单个任务的节点状态"""
        logging.info(f"检查任务: {task_config.task_name} (ID: {task_config.task_id})")

        error_nodes = []
        nodes = self.get_task_nodes(task_config.task_id)

        for node in nodes:
            # 只检查配置的节点
            if node.name not in task_config.nodes:
                continue

            logging.info(f"  节点: {node.name}, 状态: {node.status}")

            # 检查是否为错误状态
            if node.status in self.config['monitor']['error_statuses']:
                # 获取详细错误信息
                node.details = self.get_node_details(node.name)
                error_nodes.append(node)

        return error_nodes

    def run_check(self):
        """执行一次检查"""
        logging.info("=" * 50)
        logging.info(f"开始检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 50)

        try:
            self._init_browser()

            # 登录
            if not self.login():
                self.notification.send("测试系统监控：登录失败，请检查配置")
                return

            # 检查所有配置的任务
            all_errors = []
            for task in self.config['monitor']['tasks']:
                task_config = TaskConfig(
                    task_id=task['task_id'],
                    task_name=task['task_name'],
                    nodes=task['nodes']
                )

                errors = self.check_task(task_config)
                all_errors.extend(errors)

            # 发送通知
            if all_errors:
                message = self._format_error_message(all_errors)
                self.notification.send(message)
                logging.warning(f"发现 {len(all_errors)} 个错误节点")
            else:
                logging.info("所有节点状态正常")

        except Exception as e:
            logging.error(f"检查过程发生异常: {e}")
            self.notification.send(f"测试系统监控异常: {str(e)}")

        finally:
            self._close_browser()

    def _format_error_message(self, error_nodes: List[NodeStatus]) -> str:
        """格式化错误消息"""
        message = "【测试系统告警】\n\n"
        message += f"发现 {len(error_nodes)} 个节点异常:\n\n"

        for node in error_nodes:
            message += f"节点: {node.name}\n"
            message += f"状态: {node.status}\n"
            message += f"项目: {node.project}\n"
            message += f"IP: {node.ip}\n"
            if node.details:
                message += f"详情: {node.details}\n"
            message += "-" * 30 + "\n"

        message += f"\n检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message

    def run_scheduler(self):
        """运行定时调度"""
        interval = self.config['monitor']['check_interval']

        # 设置定时任务
        schedule.every(interval).minutes.do(self.run_check)

        logging.info(f"监控已启动，每 {interval} 分钟检查一次")
        logging.info("按 Ctrl+C 停止")

        # 立即执行一次
        self.run_check()

        # 保持运行
        while True:
            schedule.run_pending()
            time.sleep(1)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='测试系统监控脚本')
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='只运行一次，不启动定时任务'
    )

    args = parser.parse_args()

    monitor = TestSystemMonitor(args.config)

    if args.once:
        monitor.run_check()
    else:
        monitor.run_scheduler()


if __name__ == '__main__':
    main()
