"""基础竞品分析工具的核心数据处理纯函数模块

从 GET_Data.py 拆分出的与 GUI / Excel 写入无关的纯逻辑，
便于被其他模块导入复用及 pytest 单元测试。
本模块仅依赖标准库，禁止引入 tkinter / pandas / openpyxl。
"""
import os


def find_files(file_dir, source_type):
    """递归查找指定扩展名的所有文件

    Args:
        file_dir: 目录路径
        source_type: 文件扩展名（如 '.txt', '.zip'）

    Returns:
        list: 文件路径列表；未找到时返回空列表
    """
    file_list = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == source_type:
                file_list.append(os.path.join(root, file))
    return file_list


def decode_log_line(line):
    """将日志行字节解码为字符串

    优先按 UTF-8 解码，失败则逐字符转换（无法转换的字符替换为空格）。
    """
    try:
        return line.decode('utf-8')
    except UnicodeDecodeError:
        temp = ''
        for bchar in line:
            try:
                temp += format(bchar, 'c')
            except UnicodeDecodeError:
                temp += ' '
        return temp


def parse_txt_path(txt_file, lastfilepath=''):
    """从日志文件路径反向解析出工具名、板ID与上级路径

    路径结构约定：...\\板ID\\索引\\工具名\\文件名

    Args:
        txt_file: 日志文件完整路径
        lastfilepath: 路径层级不足时沿用的上级路径

    Returns:
        tuple: (toolname, boardID, filepath)，
        其中 boardID 带 'boardID:' 前缀
    """
    try:
        filename, toolname, indx, boardID, filepath = txt_file[::-1].split('\\', 4)
        filepath = filepath[::-1]
    except ValueError:
        # 路径层级不足时使用上次的路径
        filename, toolname, indx, boardID = txt_file[::-1].split('\\', 3)
        filepath = lastfilepath
    return toolname[::-1], 'boardID:' + boardID[::-1], filepath


def extract_config_name(get_buf):
    """从 'Config_Name:xxx.yyy' 行提取配置名（取第一个 '.' 前的部分）"""
    return get_buf.split('.', 1)[0]


def clean_matched_value(get_buf):
    """清洗关键字匹配到的日志值行：截取逗号前内容并去除首尾空白"""
    if ',' in get_buf:
        get_buf = get_buf.split(',', 1)[0]
    return get_buf.strip()


def extract_key_value_pairs(input_string):
    """提取键值对（格式：key1:value1,key2:value2）"""
    pairs = input_string.split(',')
    result = {}
    for pair in pairs:
        key_value = pair.split(':')
        if len(key_value) == 2:
            result[key_value[0]] = key_value[1]
    return result


def extract_key(key_value_pairs, key):
    """从键值对中提取指定键的值，缺失时返回 None"""
    try:
        return str(key_value_pairs[key])
    except KeyError:
        return None


def normalize_cell_value(value):
    """将原始字符串规整为可写入Excel的值

    空串/'NULL'/None 归一为 None；可转 float 的返回 float；否则返回字符串。
    """
    if value is None or value == '' or value == 'NULL':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value)
