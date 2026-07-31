#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_monitor 的核心纯逻辑模块（仅依赖标准库，供 test_monitor.py / node_monitor.py 与单元测试共用）

从两个监控脚本中抽离的与 Playwright / requests / yaml 无关的纯逻辑：
1. 配置结构校验（fail-fast，缺失关键字段时抛 ConfigValidationError 明确中止）
2. 节点状态错误判定（FAIL/FATAL/ERROR 分类）与红色错误图标样式判定
3. 节点详情文本解析（步骤号 / 工具名提取）
4. 告警消息拼装
5. URL/参数拼装（任务详情 URL、钉钉加签 webhook URL）
6. 节点表格行解析（单元格文本 -> NodeStatus）
7. 节点检查结果汇总统计与报告文本拼装
禁止在本模块引入 playwright / requests / schedule / yaml。
"""
import base64
import hashlib
import hmac
import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


# 默认视为错误的节点状态
DEFAULT_ERROR_STATUSES = ("FAIL", "FATAL", "ERROR")


class ConfigValidationError(ValueError):
    """配置结构校验失败（缺 section / 关键字段为空 / 类型不符）"""


@dataclass
class NodeStatus:
    """节点状态数据类"""
    name: str
    status: str
    project: str
    ip: str
    details: Optional[str] = None


@dataclass
class StepError:
    """步骤错误信息"""
    step_number: str      # 步骤编号（如：步骤17）
    tool_name: str        # 工具名称（如：CDM）
    error_icon: str       # 错误图标类型


@dataclass
class NodeCheckResult:
    """节点检查结果"""
    node_name: str
    task_name: str       # 节点当前运行的任务
    ip: str
    status: str          # 节点整体状态（如：FAIL）
    errors: List[StepError]  # 出错的步骤列表
    has_error: bool


def validate_config(config, mode):
    """
    校验监控配置结构，汇总所有问题后一次性抛出
    :param config: yaml.safe_load 得到的配置 dict
    :param mode: "task"（test_monitor.py 按任务监控）或 "node"（node_monitor.py 按节点监控）
    :raises ConfigValidationError: 结构不完整时抛出，消息中列出全部缺失项
    """
    if mode not in ("task", "node"):
        raise ValueError(f"未知的校验模式: {mode}")
    if not isinstance(config, dict):
        raise ConfigValidationError("配置文件内容必须是字典（yaml 顶层映射）")

    errors = []

    # test_system 登录信息为两种模式共用
    test_system = config.get("test_system")
    if not isinstance(test_system, dict):
        errors.append("缺少 test_system 配置段")
    else:
        for key in ("url", "username", "password"):
            if not test_system.get(key):
                errors.append(f"test_system.{key} 缺失或为空")

    monitor = config.get("monitor")
    if not isinstance(monitor, dict):
        errors.append("缺少 monitor 配置段")
    elif mode == "task":
        tasks = monitor.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            errors.append("monitor.tasks 缺失或为空列表")
        else:
            for i, task in enumerate(tasks):
                if not isinstance(task, dict):
                    errors.append(f"monitor.tasks[{i}] 必须是字典")
                    continue
                for key in ("task_id", "task_name"):
                    if not task.get(key):
                        errors.append(f"monitor.tasks[{i}].{key} 缺失或为空")
                if not isinstance(task.get("nodes"), list) or not task.get("nodes"):
                    errors.append(f"monitor.tasks[{i}].nodes 缺失或为空列表")
        if not isinstance(monitor.get("error_statuses"), list) or not monitor.get("error_statuses"):
            errors.append("monitor.error_statuses 缺失或为空列表")
    else:  # mode == "node"
        nodes = monitor.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            errors.append("monitor.nodes 缺失或为空列表")

    if errors:
        raise ConfigValidationError(
            "监控配置结构校验失败，已中止：\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


def is_error_status(status, error_statuses=DEFAULT_ERROR_STATUSES):
    """判断节点状态是否属于错误状态集合"""
    return status in error_statuses


def is_red_style(style):
    """判断元素 style 字符串是否表示红色（错误图标的多种红色写法）"""
    style = style or ""
    return (
        'rgb(255, 0, 0)' in style
        or 'rgb(255,0,0)' in style
        or '#ff0000' in style.lower()
        or '#f00' in style.lower()
        or 'color: red' in style.lower()
    )


def extract_step_number(text):
    """从文本中提取步骤号（如 "步骤17"），未找到返回空字符串"""
    match = re.search(r'步骤(\d+)', text or "")
    return f"步骤{match.group(1)}" if match else ""


def extract_tool_name(text):
    """从文本中提取 "工具:" 后的工具名，未找到返回空字符串"""
    if not text or '工具:' not in text:
        return ""
    parts = text.split('工具:', 1)[1].split()
    return parts[0] if parts else ""


def build_task_url(base_url: str, task_id: str) -> str:
    """拼装任务详情页 URL（保持与原实现一致的简单拼接）"""
    return f"{base_url}/task/{task_id}"


def build_dingtalk_signed_url(webhook_url: str, secret: str, timestamp_ms: Optional[str] = None) -> str:
    """
    钉钉 webhook 加签：按官方算法追加 timestamp 与 sign 参数
    :param timestamp_ms: 毫秒时间戳字符串，默认取当前时间（测试时可注入固定值）
    """
    if timestamp_ms is None:
        timestamp_ms = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp_ms}\n{secret}"
    hmac_code = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return f"{webhook_url}&timestamp={timestamp_ms}&sign={sign}"


def parse_node_row(cell_texts: List[str]) -> Optional[NodeStatus]:
    """
    从任务节点表格一行的单元格文本解析 NodeStatus
    列映射：cells[2]=节点名称, cells[6]=项目, cells[7]=状态, cells[8]=IP（可缺省）
    单元格不足 8 列时返回 None（与原实现跳过该行的行为一致）
    """
    if len(cell_texts) < 8:
        return None
    return NodeStatus(
        name=cell_texts[2].strip(),
        status=cell_texts[7].strip(),
        project=cell_texts[6].strip(),
        ip=cell_texts[8].strip() if len(cell_texts) > 8 else "",
    )


def summarize_results(results: List[Optional[NodeCheckResult]]) -> Tuple[int, int, int]:
    """
    汇总节点检查结果，返回 (正常数, 异常数, 未找到数)
    列表元素允许为 None（检查失败占位），与异常/未找到一样不计入正常数
    """
    error_count = sum(1 for r in results if r and r.has_error)
    not_found_count = sum(1 for r in results if r and r.status == "NOT_FOUND")
    normal_count = len(results) - error_count - not_found_count
    return normal_count, error_count, not_found_count


def format_node_results_report(results: List[Optional[NodeCheckResult]],
                               check_time: Optional[datetime] = None) -> str:
    """
    拼装节点监控检查结果报告文本（node_monitor 本地显示用）
    :param check_time: 检查时间，默认取当前时间（测试时可注入固定值）
    """
    if check_time is None:
        check_time = datetime.now()

    normal_count, error_count, not_found_count = summarize_results(results)

    lines = [
        "",
        "=" * 60,
        "节点监控检查结果",
        "=" * 60,
        f"检查时间: {check_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"检查节点数: {len(results)}",
        "=" * 60,
        "",
        f"正常节点: {normal_count}",
        f"异常节点: {error_count}",
        f"未找到节点: {not_found_count}",
    ]

    if error_count > 0:
        lines += ["", "-" * 60, "【异常节点详情】", "-" * 60]
        for result in results:
            if result and result.has_error:
                lines += [
                    "",
                    f"❌ 节点: {result.node_name}",
                    f"   IP: {result.ip}",
                    f"   任务: {result.task_name}",
                    f"   状态: {result.status}",
                    "   错误步骤:",
                ]
                for error in result.errors:
                    lines.append(f"     - {error.step_number}: {error.tool_name} ({error.error_icon})")

    if not_found_count > 0:
        lines += ["", "-" * 60, "【未找到的节点】", "-" * 60]
        for result in results:
            if result and result.status == "NOT_FOUND":
                lines.append(f"   - {result.node_name}")

    lines += ["", "=" * 60]
    return "\n".join(lines)


def format_error_message(error_nodes: List[NodeStatus], check_time: Optional[datetime] = None) -> str:
    """
    拼装告警消息文本
    :param error_nodes: 错误节点列表（NodeStatus 或具备同名属性的对象）
    :param check_time: 检查时间，默认取当前时间（测试时可注入固定值）
    """
    if check_time is None:
        check_time = datetime.now()

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

    message += f"\n检查时间: {check_time.strftime('%Y-%m-%d %H:%M:%S')}"
    return message
