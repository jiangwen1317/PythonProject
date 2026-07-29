# -*- coding: utf-8 -*-
"""
pytest 共享配置

将 claudecode-analysis-engine 目录加入 sys.path，
使测试可以以包形式导入 src (src 内部使用相对导入)。
"""

import os
import sys

# claudecode-analysis-engine 根目录
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)
