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


# HD Tune 平滑度数据的两类配置名（含 CA 前缀变体）
HD_TUNE_IDA_CONFIGS = ("HD Tune-IDA", "CA-HD Tune-IDA")
HD_TUNE_CLEAN_CONFIGS = ("HD Tune-CLEAN", "CA-HD Tune-CLEAN")


def hd_tune_sheet_kind(config_name):
    """判定 HD Tune 配置名归属的平滑度工作表类别

    Returns:
        'IDA' / 'CLEAN'；非 HD Tune 配置返回 None
    """
    if config_name in HD_TUNE_IDA_CONFIGS:
        return 'IDA'
    if config_name in HD_TUNE_CLEAN_CONFIGS:
        return 'CLEAN'
    return None


def parse_hd_tune_speed_values(line):
    """从 Performance.csv 的一行中分离并解析写/读速度值

    行格式：boardID:xxx,Config_Name:xxx,WriteSpeed:23,,WriteSpeed:24,,...,
    摘要字段(如 TLC_Seq_Write:23),...,ReadSpeed:306,,ReadSpeed:310,,...
    以第一个 'ReadSpeed:' 为分界：前段提取 WriteSpeed 数值，
    后段提取 ReadSpeed 数值；带冒号的摘要字段一律排除。

    Returns:
        tuple: (write_values, read_values)，均为 int 列表
    """
    write_values = []  # 顺序写速度值
    read_values = []   # 顺序读速度值

    if "ReadSpeed:" in line:
        write_part, read_part = line.split("ReadSpeed:", 1)
    else:
        write_part = line
        read_part = ""

    # 从写数据段提取WriteSpeed数值
    for segment in write_part.split("WriteSpeed:"):
        segment = segment.strip().rstrip(',').strip()
        if not segment:
            continue
        # 取逗号前的数值（排除摘要字段如 "TLC_Seq_Write:23"）
        val = segment.split(',')[0].strip()
        if val and ':' not in val:
            try:
                write_values.append(int(val))
            except ValueError:
                pass

    # 从读数据段提取ReadSpeed数值（去除残留的ReadSpeed:标签后逐个解析）
    remaining = read_part
    while remaining:
        # 取逗号前的第一个值
        first_val = remaining.split(',')[0].strip()
        if first_val and ':' not in first_val:
            try:
                read_values.append(int(first_val))
            except ValueError:
                pass

        # 跳到下一个ReadSpeed:标记后的值
        next_pos = remaining.find("ReadSpeed:")
        if next_pos == -1:
            break
        remaining = remaining[next_pos + len("ReadSpeed:"):]

    return write_values, read_values


def diff_cell_maps(map_a, map_b, max_samples=5):
    """对比两份单元格值映射（{(row, col): value}），用于回归验证。

    主流程改动前后各跑一遍样例数据，比较两次输出 Excel 指定 Sheet 的全部
    非空单元格，即可判断行为是否发生回归。与 openpyxl 解耦：调用方负责
    把 Sheet 读成 {(row, col): value} 映射，本函数只做纯对比。

    Args:
        map_a: 基准版单元格映射
        map_b: 对比版单元格映射
        max_samples: 差异示例最多返回的键数量

    Returns:
        dict: {'same': bool, 'count_a': int, 'count_b': int, 'diff_keys': list}
        其中 diff_keys 为取值不同或仅存在于一侧的坐标，按排序截取前 max_samples 个。
    """
    keys_a, keys_b = set(map_a), set(map_b)
    diff_keys = sorted(
        keys_a ^ keys_b | {k for k in keys_a & keys_b if map_a[k] != map_b[k]}
    )
    return {
        'same': not diff_keys,
        'count_a': len(map_a),
        'count_b': len(map_b),
        'diff_keys': diff_keys[:max_samples],
    }
