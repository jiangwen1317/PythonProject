"""关键字数据汇总工具的核心提取逻辑模块

从 keyword_extraction.py 拆分出的与 GUI 无关的可测逻辑，
便于被其他模块导入复用及 pytest 单元测试。
本模块仅依赖标准库，禁止引入 tkinter / openpyxl。
"""
import os
import zipfile


def extract_content_after_keyword(txt_path, keyword, last_only=True):
    """
    从TXT文件中提取指定关键字后的内容（关键字带冒号，如 "Max_Seq_Rd_Spd:"）
    - 如果 last_only=True（默认）：返回最后一次出现的最后一个非空逗号值
    - 如果 last_only=False：返回所有匹配行中提取出的值（列表）
    """
    try:
        encodings = ['utf-8', 'gbk', 'latin1']
        for encoding in encodings:
            try:
                with open(txt_path, 'r', encoding=encoding) as file:
                    lines = file.readlines()

                key_clean = keyword.strip()
                all_results = []

                # 全部模式正序遍历，否则倒序（取最后一次）
                search_lines = reversed(lines) if last_only else lines

                for line in search_lines:
                    stripped_line = line.strip()
                    if not stripped_line.startswith(key_clean):
                        continue

                    content_start = len(key_clean)
                    if content_start >= len(stripped_line):
                        continue
                    content = stripped_line[content_start:].lstrip()

                    parts = [p.strip() for p in content.split(',') if p.strip()]
                    if parts:
                        value = parts[-1]
                        if last_only:
                            return value  # 立即返回最后一次
                        else:
                            all_results.append(value)

                if last_only:
                    return None
                else:
                    return all_results or None

            except (UnicodeDecodeError, PermissionError):
                continue
        return None
    except Exception as e:
        print(f"【错误】读取文件失败 {txt_path}: {e}")
        return None


def extract_nested_zips(start_dir, max_iterations=2):
    """
    递归解压所有 ZIP 文件，并在解压成功后删除原压缩包
    :param start_dir: 起始目录
    :param max_iterations: 最大解压轮数（防止无限循环）
    """
    print(f"【开始】深度解压 {start_dir} 下的所有 ZIP 文件，并删除压缩包...")

    for iteration in range(1, max_iterations + 1):
        extracted = False
        zip_files = []

        # 遍历收集所有 ZIP 文件
        for root, _, files in os.walk(start_dir):
            for file in files:
                if file.lower().endswith('.zip'):
                    zip_files.append(os.path.join(root, file))

        if not zip_files:
            print(f"【完成】第 {iteration} 轮：未发现 ZIP 文件，停止解压。")
            break

        print(f"【解压】第 {iteration} 轮：发现 {len(zip_files)} 个 ZIP 文件...")

        # 逐个解压并删除
        for zip_path in zip_files:
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(os.path.dirname(zip_path))
                print(f"          已解压: {os.path.basename(zip_path)}")

                # ✅ 解压成功后删除原 ZIP 文件
                os.remove(zip_path)
                print(f"          已删除: {os.path.basename(zip_path)}")
                extracted = True

            except Exception as e:
                print(f"          解压失败: {os.path.basename(zip_path)} - {e}")
                # 解压失败时不删除文件，保留以便检查
                continue

        if not extracted:
            print(f"【完成】第 {iteration} 轮后无新文件解压，结束。")
            break

    print("【清理】所有可解压的 ZIP 文件已处理并删除。")


def get_config_name(txt_file):
    """从 txt 文件中找 Config_Name: 或 Device_Config_Name:，返回第一个找到的值"""
    for keyword in ["Config_Name:", "Device_Config_Name       :"]:
        value = extract_content_after_keyword(txt_file, keyword)
        if value:
            # 去掉换行和 .log 这类后缀（比如 "cfg.log" → "cfg"）
            val = value.strip()
            return val
    return ""


def build_wide_rows(records):
    """把长记录聚合为宽表行结构（纯逻辑，不做任何 Excel 写入）

    输入 records: 可迭代 (board_id, script, config_name, keyword, value)，
    调用方需保证按文件处理顺序传入；同一 (板子, 配置, 关键字) 后出现的值覆盖先前值。

    返回 (board_columns, rows)：
    - board_columns: 板子号（节点列）有序列表，按首次出现顺序；
    - rows: dict 列表，每项含 script / config / keyword / values（values 为
      {板子号: 值} 映射），行顺序为配置首次出现顺序，同配置内关键字保持首次出现顺序。
    """
    board_columns = []
    board_index = set()
    row_order = []  # (config, keyword) 有序去重
    row_values = {}  # (config, keyword) -> {board: value}
    row_script = {}  # config -> script（配置名唯一对应一个脚本，随最后处理文件更新）

    for board_id, script, config_name, keyword, value in records:
        if board_id not in board_index:
            board_index.add(board_id)
            board_columns.append(board_id)

        row_key = (config_name, keyword)
        if row_key not in row_values:
            row_values[row_key] = {}
            row_order.append(row_key)
        row_values[row_key][board_id] = value

        if script:
            row_script[config_name] = script

    rows = [
        {
            "script": row_script.get(config, ""),
            "config": config,
            "keyword": keyword,
            "values": row_values[(config, keyword)],
        }
        for config, keyword in row_order
    ]
    return board_columns, rows

