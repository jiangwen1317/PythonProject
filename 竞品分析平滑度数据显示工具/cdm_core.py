"""竞品分析平滑度数据显示工具的核心纯函数模块

从 CDM_RandomRead.py 拆分出的与 GUI / matplotlib / pandas 无关的纯逻辑，
便于被其他模块导入复用及 pytest 单元测试。
本模块仅依赖标准库，禁止引入 PySimpleGUI / matplotlib / pandas。
"""
import os
import random


#随机分配颜色代码
def getColor(n):
    color1 = random.sample(range(16, 255), n)
    color2 = random.sample(range(16, 250), n)
    color3 = random.sample(range(16, 250), n)
    for i in range(n):
        color1[i] = hex(color1[i])
        color2[i] = hex(color2[i])
        color3[i] = hex(color3[i])
    ans = []
    for i in range(n):
        ans.append("#" + color1[i][2:] + color2[i][2:] + color3[i][2:])
    return ans

#判断字符串是否为数字
def is_number(n):
    try:
        int(n)
        return True
    except ValueError:
        return False

#查找符合文件类型的文件
def file_name(file_dir,source_type):   
    L=[]
    for root, dirs, files in os.walk(file_dir):  
        for file in files:  
            if os.path.splitext(file)[1] == source_type:  
               L.append(os.path.splitext(file)[0])
    return L 
