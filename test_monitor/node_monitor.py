#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式测试系统节点监控脚本
流程：登录 -> 搜索节点 -> 进入节点详情 -> 展开步骤 -> 检查错误状态 -> 本地显示结果
"""

import yaml
import time
import logging
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, expect

from monitor_core import (
    NodeCheckResult,
    StepError,
    extract_step_number,
    extract_tool_name,
    format_node_results_report,
    is_red_style,
    validate_config,
)


class NodeMonitor:
    """节点监控器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._setup_logging()

    def _load_config(self, config_path: str) -> Dict:
        """加载并校验配置文件（结构不完整时 fail-fast）"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        validate_config(config, mode="node")
        return config

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

    def _init_browser(self, headless: bool = True):
        """初始化浏览器（使用系统已安装的Chrome）"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            channel="chrome",  # 使用系统安装的Chrome浏览器
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = self.browser.new_page()
        self.page.set_viewport_size({'width': 1920, 'height': 1080})

    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.browser = None
        self.page = None
        self.playwright = None

    def login(self) -> bool:
        """
        登录测试系统
        """
        try:
            test_system = self.config['test_system']
            url = test_system['url']
            username = test_system['username']
            password = test_system['password']

            logging.info(f"正在登录测试系统: {url}")
            self.page.goto(url, wait_until='networkidle')

            # 等待登录表单加载
            self.page.wait_for_selector('input', timeout=10000)

            # 填写用户名 - 找第一个可见的文本输入框
            username_input = self.page.query_selector('input[type="text"], input:not([type="password"])')
            if username_input:
                username_input.fill(username)
                logging.info("已输入用户名")
            else:
                logging.error("未找到用户名输入框")
                return False

            # 填写密码
            password_input = self.page.query_selector('input[type="password"]')
            if password_input:
                password_input.fill(password)
                logging.info("已输入密码")
            else:
                logging.error("未找到密码输入框")
                return False

            # 点击登录按钮
            login_button = self.page.query_selector('button:has-text("登录"), button[type="submit"], .el-button--primary')
            if login_button:
                login_button.click()
                logging.info("已点击登录按钮")
            else:
                logging.error("未找到登录按钮")
                return False

            # 等待页面跳转 - 等待URL变化或页面内容变化
            self.page.wait_for_timeout(3000)
            
            # 检查是否登录成功 - 通过检查页面是否还有登录按钮来判断
            login_button_still = self.page.query_selector('button:has-text("登录")')
            if login_button_still and login_button_still.is_visible():
                logging.error("登录失败，可能密码错误")
                return False

            logging.info("登录成功")
            return True

        except Exception as e:
            logging.error(f"登录失败: {e}")
            try:
                self.page.screenshot(path='login_error.png')
                logging.info("已保存登录错误截图: login_error.png")
            except:
                pass
            return False

    def navigate_to_node_list(self) -> bool:
        """
        导航到节点列表页面（图二）
        """
        try:
            # 点击左侧菜单"节点列表"
            node_list_menu = self.page.query_selector('text=节点列表')
            if node_list_menu:
                node_list_menu.click()
                # 等待节点列表表格加载
                self.page.wait_for_selector('table, .el-table', timeout=10000)
                logging.info("已进入节点列表页面")
                return True
            else:
                # 可能已经在节点列表页面
                if self.page.query_selector('table, .el-table'):
                    logging.info("当前已在节点列表页面")
                    return True
                logging.error("未找到节点列表菜单")
                return False

        except Exception as e:
            logging.error(f"导航到节点列表失败: {e}")
            return False

    def return_to_node_list(self) -> bool:
        """
        检查完一个节点后，返回节点列表页面
        """
        try:
            # 点击左侧菜单中的"节点列表"
            node_list_link = self.page.locator('text="节点列表"').first
            if node_list_link.count() > 0 and node_list_link.is_visible():
                node_list_link.click()
                self.page.wait_for_timeout(1000)
                logging.info("已返回节点列表页面")
                return True
            else:
                logging.warning("未找到节点列表菜单项")
        except Exception as e:
            logging.warning(f"返回节点列表失败: {e}")
        return False

    def search_node(self, node_name: str) -> bool:
        """
        搜索指定节点
        点击搜索按钮 -> 勾选全局搜索 -> 输入节点号 -> 点击确定
        """
        try:
            logging.info(f"正在搜索节点: {node_name}")

            # 1. 点击搜索按钮（iView 图标）
            search_button = self.page.locator('i.ivu-icon-ios-search, .ivu-icon-ios-search').first
            if search_button.count() > 0:
                search_button.click()
                logging.info("已点击搜索按钮")
            else:
                logging.error("未找到搜索按钮")
                self.page.screenshot(path='search_button_error.png')
                return False

            # 2. 等待搜索弹窗出现（iView Modal）
            # 等待可见的弹窗（排除隐藏的）
            self.page.wait_for_selector('.ivu-modal-wrap:not(.ivu-modal-hidden)', timeout=5000)
            self.page.wait_for_timeout(500)
            logging.info("搜索弹窗已打开")

            # 3. 勾选"全局搜索"复选框
            global_checkbox = self.page.locator('label:has-text("全局搜索"), .ivu-checkbox-wrapper:has-text("全局搜索")').first
            if global_checkbox.count() > 0:
                # 检查是否已勾选
                checkbox_input = global_checkbox.locator('input[type="checkbox"]').first
                if checkbox_input.count() > 0 and not checkbox_input.is_checked():
                    global_checkbox.click()
                    logging.info("已勾选全局搜索")
                    self.page.wait_for_timeout(300)
            else:
                logging.warning("未找到全局搜索复选框")

            # 4. 在搜索输入框中输入节点号
            # 找到可见的输入框
            dialog = self.page.locator('.ivu-modal-wrap:not(.ivu-modal-hidden) .ivu-modal-body')
            # 遍历所有输入框，找到可见的那个
            inputs = dialog.locator('input.ivu-input')
            search_input = None
            for i in range(inputs.count()):
                inp = inputs.nth(i)
                if inp.is_visible():
                    search_input = inp
            
            if search_input:
                search_input.fill(node_name)
                logging.info(f"已输入节点号: {node_name}")
            else:
                logging.error("未找到可见的搜索输入框")
                self.page.screenshot(path='search_input_error.png')
                return False

            # 5. 点击确定按钮（在可见的弹窗中）
            visible_modal = self.page.locator('.ivu-modal-wrap:not(.ivu-modal-hidden)')
            confirm_button = visible_modal.locator('.ivu-modal-footer button:has-text("确定"), .ivu-modal-footer .ivu-btn-primary').first
            if confirm_button.count() > 0 and confirm_button.is_visible():
                confirm_button.click()
                logging.info("已点击确定按钮")
            else:
                logging.error("未找到可见的确定按钮")
                self.page.screenshot(path='confirm_button_error.png')
                return False

            # 6. 等待搜索结果加载
            self.page.wait_for_timeout(2000)

            # 7. 检查是否有搜索结果 - 查找表格中包含节点名的单元格
            node_cell = self.page.locator(f'td:has-text("{node_name}")').first
            if node_cell and node_cell.is_visible():
                logging.info(f"搜索完成，找到节点: {node_name}")
                return True
            else:
                logging.warning(f"未找到节点: {node_name}")
                self.page.screenshot(path='search_result_error.png')
                return False

        except Exception as e:
            logging.error(f"搜索节点失败: {e}")
            self.page.screenshot(path='search_error.png')
            return False

    def enter_node_detail(self, node_name: str) -> bool:
        """
        双击节点进入详情页面（图四 -> 图五）
        """
        try:
            logging.info(f"正在进入节点详情: {node_name}")

            # 查找节点行并双击
            # 先尝试精确匹配
            node_cell = self.page.query_selector(f'text="{node_name}"')
            if not node_cell:
                # 尝试包含匹配
                node_cell = self.page.query_selector(f'text={node_name}')

            if node_cell:
                # 双击进入详情
                node_cell.dblclick()
                logging.info(f"已双击节点: {node_name}")
            else:
                logging.error(f"未找到节点: {node_name}")
                return False

            # 等待节点详情页面加载（图五）
            # 图五显示的是节点详情，有步骤列表
            self.page.wait_for_timeout(2000)

            # 检查是否进入详情页（页面标题应该包含节点名）
            page_title = self.page.title()
            if node_name in page_title or self.page.query_selector(f'text="{node_name}"'):
                logging.info("已进入节点详情页面")
                return True
            else:
                logging.warning("可能未正确进入节点详情页面")
                return False

        except Exception as e:
            logging.error(f"进入节点详情失败: {e}")
            return False

    def expand_and_check_steps(self) -> Tuple[List[StepError], str, str]:
        """
        展开所有步骤并检查错误状态
        返回: (错误步骤列表, 节点IP, 任务名称)
        """
        errors = []
        node_ip = ""
        task_name = ""

        try:
            # 1. 获取节点IP
            ip_element = self.page.locator('text=/\\d+\\.\\d+\\.\\d+\\.\\d+/').first
            if ip_element.count() > 0:
                node_ip = ip_element.inner_text().strip()
                logging.info(f"节点IP: {node_ip}")

            # 2. 点击齿轮按钮展开步骤列表
            expand_button = self.page.locator('i.ivu-icon-md-settings').first
            if expand_button.count() > 0 and expand_button.is_visible():
                expand_button.click()
                logging.info("已点击展开按钮")
                self.page.wait_for_timeout(1500)  # 等待步骤列表加载
            else:
                logging.warning("未找到展开按钮")

            # 3. 滚动查看所有步骤
            self.page.wait_for_timeout(500)

            # 4. 查找所有红色错误图标，然后找对应的步骤
            # 红色图标: <i class="ivu-icon-md-close-circle" style="color: rgb(255, 0, 0);">
            all_close_icons = self.page.locator('i.ivu-icon-md-close-circle').all()
            logging.info(f"找到 {len(all_close_icons)} 个 close-circle 图标")
            
            for icon in all_close_icons:
                try:
                    if not icon.is_visible():
                        continue
                    
                    # 检查是否是红色
                    style = icon.get_attribute('style') or ''

                    # 多种红色写法的判定在 monitor_core.is_red_style
                    if not is_red_style(style):
                        continue  # 跳过非红色图标

                    # 找到红色图标，现在往上找步骤号和工具名
                    # 往上查找最近的包含 "工具:" 的元素
                    parent = icon.locator('xpath=..')
                    tool_text = parent.inner_text().strip() if parent.count() > 0 else ''

                    # 提取工具名称
                    tool_name = extract_tool_name(tool_text)

                    # 往上查找步骤号（可能需要往上多层）
                    step_number = ""

                    # 尝试往上查找多层，直到找到“步骤”
                    for level in range(2, 8):  # 从 ../.. 到 ../../../../../../..
                        xpath_up = '/'.join(['..'] * level)
                        ancestor = icon.locator(f'xpath={xpath_up}')
                        if ancestor.count() > 0:
                            try:
                                anc_text = ancestor.inner_text()
                                step_number = extract_step_number(anc_text)
                                if step_number:
                                    break
                            except:
                                continue
                    
                    if not step_number:
                        logging.warning("未找到步骤号")
                        continue
                    
                    if step_number and step_number not in [e.step_number for e in errors]:
                        error = StepError(
                            step_number=step_number,
                            tool_name=tool_name or "未知工具",
                            error_icon="❌"
                        )
                        errors.append(error)
                        logging.warning(f"发现红色错误: {step_number} - {tool_name}")
                
                except Exception as e:
                    logging.warning(f"解析错误图标时出错: {e}")
                    continue

            # 6. 如果没找到错误，检查页面上是否有 FAIL 状态
            if len(errors) == 0:
                fail_indicator = self.page.locator('text=FAIL, text=FATAL, text=ERROR').first
                if fail_indicator.count() > 0 and fail_indicator.is_visible():
                    errors.append(StepError(
                        step_number="未知",
                        tool_name="未知",
                        error_icon="FAIL"
                    ))
                    logging.warning("页面显示 FAIL 状态")

        except Exception as e:
            logging.error(f"检查步骤时出错: {e}")

        return errors, node_ip, task_name

    def check_node(self, node_name: str) -> Optional[NodeCheckResult]:
        """
        检查单个节点的完整流程
        """
        logging.info(f"\n{'='*50}")
        logging.info(f"开始检查节点: {node_name}")
        logging.info(f"{'='*50}")

        try:
            # 1. 导航到节点列表
            if not self.navigate_to_node_list():
                return None

            # 2. 搜索节点
            if not self.search_node(node_name):
                return NodeCheckResult(
                    node_name=node_name,
                    task_name="",
                    ip="",
                    status="NOT_FOUND",
                    errors=[],
                    has_error=False
                )

            # 3. 获取节点状态（从搜索结果表格中）
            status = "UNKNOWN"
            status_el = self.page.query_selector('td .el-tag--danger, td:has-text("FAIL"), td:has-text("FATAL")')
            if status_el:
                status = status_el.inner_text().strip()

            # 4. 进入节点详情
            if not self.enter_node_detail(node_name):
                return NodeCheckResult(
                    node_name=node_name,
                    task_name="",
                    ip="",
                    status=status,
                    errors=[],
                    has_error=status in ["FAIL", "FATAL"]
                )

            # 5. 展开并检查步骤
            errors, node_ip, task_name = self.expand_and_check_steps()

            result = NodeCheckResult(
                node_name=node_name,
                task_name=task_name,
                ip=node_ip,
                status=status,
                errors=errors,
                has_error=len(errors) > 0
            )

            logging.info(f"节点检查完成: {node_name}, 发现 {len(errors)} 个错误")
            
            # 6. 返回节点列表，为下一个节点检查做准备
            self.return_to_node_list()
            
            return result

        except Exception as e:
            logging.error(f"检查节点 {node_name} 时发生异常: {e}")
            return None

    def display_results(self, results: List[NodeCheckResult]):
        """
        在本地显示检查结果（汇总与拼装逻辑在 monitor_core.format_node_results_report）
        """
        print(format_node_results_report(results))

    def run(self, headless: bool = True, debug_pause: bool = False):
        """
        运行监控
        debug_pause: 调试模式，每步操作后暂停等待用户确认
        """
        nodes_to_check = self.config['monitor']['nodes']
        results = []

        try:
            self._init_browser(headless=headless)

            # 登录
            if not self.login():
                print("登录失败，请检查配置")
                return

            print("登录成功！")

            # 检查每个节点
            for node_name in nodes_to_check:
                result = self.check_node(node_name)
                if result:
                    results.append(result)
                else:
                    results.append(NodeCheckResult(
                        node_name=node_name,
                        task_name="",
                        ip="",
                        status="CHECK_FAILED",
                        errors=[],
                        has_error=False
                    ))

            # 显示结果
            self.display_results(results)

        except Exception as e:
            logging.error(f"运行监控时发生异常: {e}")
            print(f"运行出错: {e}")

        finally:
            self._close_browser()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='分布式测试系统节点监控')
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--visible',
        action='store_true',
        help='显示浏览器窗口（用于调试）'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='调试模式，每步操作后暂停等待确认'
    )

    args = parser.parse_args()

    monitor = NodeMonitor(args.config)
    monitor.run(headless=not args.visible, debug_pause=args.debug)


if __name__ == '__main__':
    main()
