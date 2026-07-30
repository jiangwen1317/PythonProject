#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置校验纯逻辑模块（仅依赖标准库，供 Data_Summarization.py 与单元测试共用）

职责：
1. 加载配置文件夹下的所有 .json 测试项配置（解析失败即报错，不静默跳过）
2. 校验每个配置组引用的 sheet_name 在目标模板的工作表列表中确实存在，
   命中缺失时抛出 ConfigValidationError 明确中止，而非 print 后跳过
"""
import json
import os


class ConfigValidationError(ValueError):
    """配置校验失败（JSON 解析失败 / sheet_name 缺失或不在模板中）"""


def normalize_sheet_configs(config_data):
    """单个 JSON 顶层可以是 dict 或 list，统一转为配置组列表"""
    return config_data if isinstance(config_data, list) else [config_data]


def load_config_folder(config_folder):
    """
    加载配置文件夹下所有 .json 文件（按文件名排序）
    :return: [(文件名, [配置组, ...]), ...]
    :raises ConfigValidationError: 路径不是文件夹 / 无 .json 文件 / 任一文件解析失败
    """
    if not os.path.isdir(config_folder):
        raise ConfigValidationError(f"配置路径必须是文件夹: {config_folder}")

    json_files = sorted(
        f for f in os.listdir(config_folder) if f.lower().endswith('.json')
    )
    if not json_files:
        raise ConfigValidationError(f"配置文件夹中未找到任何 .json 文件: {config_folder}")

    loaded = []
    for file_name in json_files:
        file_path = os.path.join(config_folder, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            raise ConfigValidationError(f"配置文件加载失败: {file_name} - {e}")
        loaded.append((file_name, normalize_sheet_configs(config_data)))
    return loaded


def validate_sheet_configs(loaded_configs, template_sheetnames):
    """
    校验所有配置组引用的 sheet_name 在模板工作表列表中存在
    :param loaded_configs: load_config_folder 的返回值
    :param template_sheetnames: 模板中的工作表名列表
    :raises ConfigValidationError: 一次性汇总所有缺失项后抛出
    """
    available = set(template_sheetnames)
    errors = []
    for file_name, sheet_configs in loaded_configs:
        for group_config in sheet_configs:
            sheet_name = group_config.get("sheet_name")
            if not sheet_name:
                errors.append(f"配置文件 '{file_name}' 存在未定义 sheet_name 的配置组")
            elif sheet_name not in available:
                errors.append(f"配置文件 '{file_name}' 引用的工作表 '{sheet_name}' 在模板中不存在")

    if errors:
        raise ConfigValidationError(
            "配置与模板不匹配，已中止处理：\n"
            + "\n".join(f"  - {e}" for e in errors)
            + "\n模板可用工作表：" + "、".join(template_sheetnames)
        )
