# 将工具目录加入 sys.path，使测试可直接 import monitor_core
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
