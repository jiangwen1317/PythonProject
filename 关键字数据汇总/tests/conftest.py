# 将工具目录加入 sys.path，使测试可直接 import extraction_core
# （目录名为中文，无法作为常规包导入）
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
