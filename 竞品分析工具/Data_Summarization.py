#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极增强版处理器：支持普通数据提取 + 分组百分比计算 + 按 JSON 工具组合并到同一行
📌 统一配置入口：仅支持配置文件夹（自动加载所有 .json），兼容单文件场景
✅ 新增功能：为每一行写入的数据范围（A列到Z列）自动添加边框
"""
import os
import zipfile
import tempfile
import shutil
import openpyxl
from openpyxl.utils import column_index_from_string
from openpyxl.styles import Alignment, Border, Side  # ✅ 新增 Border, Side
from openpyxl.utils import get_column_letter
import sys

from config_core import ConfigValidationError, load_config_folder, validate_sheet_configs


def get_exe_dir():
    """获取当前 .exe 或 .py 文件所在的目录（用于定位 template.xlsx 和 json/）"""
    if getattr(sys, 'frozen', False):
        # 打包成 .exe 的情况
        return os.path.dirname(sys.executable)
    else:
        # 以 .py 脚本运行的情况
        return os.path.dirname(os.path.abspath(__file__))

def extract_content_after_keyword(txt_path, keyword, reverse_search=False, numeric_only=False, extract_all=False):
    """
    从日志文件中提取关键字后的内容
    :param extract_all: 若为 True，返回所有匹配行的值（展平列表）；否则只返回第一个/最后一个匹配
    """
    try:
        encodings = ['utf-8', 'gbk', 'latin1']
        for encoding in encodings:
            try:
                with open(txt_path, 'r', encoding=encoding) as file:
                    lines = file.readlines()

                if extract_all:
                    # 提取所有匹配行
                    all_values = []
                    for line in lines:
                        stripped_line = line.strip()
                        if stripped_line.startswith(keyword):
                            content = stripped_line[len(keyword):].strip()
                            parts = [p.strip() for p in content.split(',') if p.strip()]
                            for p in parts:
                                if numeric_only:
                                    numeric_part = ''.join(filter(lambda x: x.isdigit() or x in ['.', '-', '+', 'e'], p))
                                    try:
                                        all_values.append(float(numeric_part))
                                    except ValueError:
                                        if not extract_all:  # 原逻辑保留字符串
                                            all_values.append(p)
                                        # 否则 average 模式下可忽略非数字
                                else:
                                    all_values.append(p)
                    return all_values if all_values else None

                else:
                    # 原有逻辑：只取一个匹配（首或尾）
                    iterable_lines = reversed(lines) if reverse_search else lines
                    for line in iterable_lines:
                        stripped_line = line.strip()
                        if stripped_line.startswith(keyword):
                            content = stripped_line[len(keyword):].strip()
                            parts = [p.strip() for p in content.split(',') if p.strip()]
                            values = []
                            for p in parts:
                                if numeric_only:
                                    numeric_part = ''.join(filter(lambda x: x.isdigit() or x in ['.', '-', '+', 'e'], p))
                                    try:
                                        values.append(float(numeric_part))
                                    except ValueError:
                                        values.append(p)
                                else:
                                    values.append(p)
                            return values
                    return None

            except (UnicodeDecodeError, PermissionError):
                continue
        return None
    except Exception as e:
        print(f"【错误】读取文件失败 {txt_path}: {e}")
        return None


def extract_nested_zips(start_dir, max_iterations=2):
    """
    深度解压指定目录下的所有 ZIP 文件，并删除原始压缩包
    """
    print(f"【开始】深度解压 {start_dir} 下的所有 ZIP 文件，并删除压缩包...")
    for iteration in range(1, max_iterations + 1):
        extracted = False
        zip_files = [
            os.path.join(root, file)
            for root, _, files in os.walk(start_dir)
            for file in files
            if file.lower().endswith('.zip')
        ]
        if not zip_files:
            print(f"【完成】第 {iteration} 轮：未发现 ZIP 文件，停止解压。")
            break

        print(f"【解压】第 {iteration} 轮：发现 {len(zip_files)} 个 ZIP 文件...")
        for zip_path in zip_files:
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(os.path.dirname(zip_path))
                print(f"          已解压: {os.path.basename(zip_path)}")
                os.remove(zip_path)
                print(f"          已删除: {os.path.basename(zip_path)}")
                extracted = True
            except Exception as e:
                print(f"          解压失败: {os.path.basename(zip_path)} - {e}")
                continue
        if not extracted:
            print(f"【完成】第 {iteration} 轮后无新文件解压，结束。")
            break
    print("【清理】所有可解压的 ZIP 文件已处理并删除。")


def calculate_group_ratios(ws, row, group_config, keyword_to_col):
    """
    ✅ 计算百分比并写入为小数，强制设置格式为百分比 + 居中对齐
    """
    if not group_config.get("calculate_ratio", False):
        return

    keywords = group_config.get("keywords", [])
    if not keywords:
        print(f"【警告】分组 '{group_config.get('name', 'Unknown')}' 未定义 keywords，跳过计算")
        return

    output_columns = group_config.get("output_columns", {})
    if not output_columns:
        output_columns = {kw: keyword_to_col.get(kw, "") for kw in keywords}

    decimal_places = group_config.get("decimal_places", 4)

    values = []
    valid_keywords = []
    for kw in keywords:
        col_letter = output_columns.get(kw, "")
        if not col_letter:
            print(f"【警告】分组 '{group_config.get('name')}' 中关键字 '{kw}' 无对应列，跳过")
            continue
        try:
            col_idx = column_index_from_string(col_letter.upper())
            cell_value = ws.cell(row=row, column=col_idx).value
            if isinstance(cell_value, (int, float)):
                values.append(cell_value)
                valid_keywords.append(kw)
            else:
                values.append(0.0)
                valid_keywords.append(kw)
                print(f"【注意】关键字 '{kw}' 值非数字（{cell_value}），按0处理")
        except Exception as e:
            print(f"【错误】读取单元格失败 {kw} -> {col_letter}: {e}")
            values.append(0.0)
            valid_keywords.append(kw)

    total = sum(values)
    if total == 0:
        print(f"【注意】分组 '{group_config.get('name')}' 总和为0，跳过百分比计算")
        return

    for i, kw in enumerate(valid_keywords):
        percentage = (values[i] / total) * 100
        decimal_value = percentage / 100.0
        numeric_value = round(decimal_value, decimal_places + 2)

        col_letter = output_columns[kw]
        try:
            col_idx = column_index_from_string(col_letter.upper())
            cell = ws.cell(row=row, column=col_idx, value=numeric_value)

            # ✅ 强制设置百分比格式
            cell.number_format = '0.00%'
            # ✅ 强制居中对齐
            cell.alignment = Alignment(horizontal='center', vertical='center')

        except Exception as e:
            print(f"【错误】写入百分比失败 {kw} -> {col_letter}: {e}")


def process_folder(folder_path, excel_template, config_folder, meta_values=None):
    """
    核心处理函数：仅支持配置文件夹模式（自动加载所有 .json）
    🎯 用户只需指定一个配置文件夹，内部自动遍历所有 .json
    ✅ 兼容单 JSON 场景（文件夹里只放一个 .json 即可）
    ✅ 新增：动态确定最后一列添加边框
    """
    try:
        # --- 步骤1：加载配置文件夹下所有 .json（解析失败即中止，不静默跳过）---
        try:
            loaded_configs = load_config_folder(config_folder)
        except ConfigValidationError as e:
            return False, f"❌ {e}"

        print(f"【配置】加载 {len(loaded_configs)} 个配置文件: {[name for name, _ in loaded_configs]}")

        # --- 步骤2：解压所有 ZIP ---
        extract_nested_zips(folder_path)

        # --- 步骤3：收集所有 TXT 文件 ---
        txt_files = [
            os.path.join(root, file)
            for root, _, files in os.walk(folder_path)
            for file in files
            if file.lower().endswith('.txt')
        ]
        if not txt_files:
            return False, "❌ 未找到任何 TXT 文件！"

        # --- 步骤4：准备 Excel 写入 ---
        summary_path = os.path.join(folder_path, "Summary.xlsx")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_file.close()
        shutil.copy(excel_template, temp_file.name)
        wb = openpyxl.load_workbook(temp_file.name)

        # ✅ 写入前统一校验：配置引用的 sheet_name 必须在模板中存在，缺失即明确中止
        try:
            validate_sheet_configs(loaded_configs, wb.sheetnames)
        except ConfigValidationError as e:
            os.remove(temp_file.name)
            return False, f"❌ {e}"

        total_files_processed = 0

        # --- 步骤5：遍历每个 JSON 配置文件 ---
        for config_file_name, sheet_configs in loaded_configs:
            print(f"\n========== 加载配置: {config_file_name} ==========")

            # --- 处理该 JSON 中的每个 sheet 配置组 ---
            for group_config in sheet_configs:
                sheet_name = group_config["sheet_name"]  # 已通过前置校验，必然存在于模板
                tools = group_config.get("tools", [])

                if not tools:
                    print(f"【跳过】配置组 '{sheet_name}' 无工具定义")
                    continue

                ws = wb[sheet_name]
                print(f"\n=== 处理工作表: {sheet_name} ===")

                tool_configs = {tool["name"]: tool for tool in tools}
                group_config_names = set(tool_configs.keys())
                print(f"【工具组】包含配置: {sorted(group_config_names)}")

                matched_files = []
                for txt_file in txt_files:
                    try:
                        config_name_values = extract_content_after_keyword(
                            txt_file, "Config_Name:", reverse_search=False, numeric_only=False
                        )
                        if not config_name_values:
                            print(f"【跳过】未找到 Config_Name: {os.path.basename(txt_file)}")
                            continue

                        config_name = str(config_name_values[0]).strip()
                        if config_name in group_config_names:
                            matched_files.append((txt_file, config_name))
                            print(f"  → 匹配: {os.path.basename(txt_file)} → {config_name}")
                    except Exception as e:
                        print(f"  → 提取失败 {os.path.basename(txt_file)}: {e}")
                        continue

                if not matched_files:
                    print(f"【跳过组】{sheet_name} - 无匹配文件")
                    continue

                next_row = 5
                while ws.cell(row=next_row, column=1).value is not None:
                    next_row += 1

                print(f"【写入行 {next_row}】合并 {len(matched_files)} 个配置文件")

                # ✅ 写入用户提供的元信息到 A~E 列（仅当前行）
                if meta_values is not None:
                    for col_offset, value in enumerate(meta_values[:5], start=1):  # A=1, B=2, ..., E=5
                        cell = ws.cell(row=next_row, column=col_offset, value=value if value else "")
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    print(f"【元信息】第 {next_row} 行 A-E 已写入用户输入值")

                # --- 写入数据 ---
                for txt_file, config_name in matched_files:
                    tool_config = tool_configs[config_name]
                    keyword_to_col = tool_config.get("keyword_to_column", {})
                    post_process_rules = tool_config.get("post_process", {})
                    extract_mode = tool_config.get("extract_mode", {})  # 👈 新增：提取模式配置

                    if not keyword_to_col:
                        print(f"【跳过】工具 '{config_name}' 未定义 keyword_to_column")
                        continue

                    for keyword, target_col in keyword_to_col.items():
                        mode = extract_mode.get(keyword, "last")  # 默认行为：取最后一个

                        if mode == "average_all":
                            # 🆕 提取所有值并计算平均
                            all_values = extract_content_after_keyword(
                                txt_file, keyword, reverse_search=False, numeric_only=True, extract_all=True
                            )
                            if not all_values:
                                output_value = None
                            else:
                                # 过滤掉非数字（虽然 numeric_only=True 应该都是数字，但保险）
                                numeric_vals = [v for v in all_values if isinstance(v, (int, float))]
                                if numeric_vals:
                                    output_value = sum(numeric_vals) / len(numeric_vals)
                                else:
                                    output_value = None
                        else:
                            # 原有逻辑：取最后一个
                            values = extract_content_after_keyword(
                                txt_file, keyword, reverse_search=True, numeric_only=True
                            )
                            output_value = values[0] if values else None

                        if output_value is None:
                            continue

                        # 应用后处理
                        rule = post_process_rules.get(keyword, {})
                        transform = rule.get("transform")
                        if isinstance(output_value, (int, float)):
                            if transform == "divide_1024":
                                output_value = round(output_value / 1024.0, 1)
                            elif transform == "divide_1000":
                                output_value = round(output_value / 1000.0, 3)
                            # 可继续扩展其他 transform，如 "multiply_2", "to_kib", 等

                        try:
                            col_idx = column_index_from_string(target_col.upper())
                            cell = ws.cell(row=next_row, column=col_idx, value=output_value)
                            cell.alignment = Alignment(horizontal='center', vertical='center')
                        except ValueError:
                            print(f"【警告】无效列名: {target_col} (工具: {config_name})")

                # --- 执行分组计算 ---
                for txt_file, config_name in matched_files:
                    tool_config = tool_configs[config_name]
                    group_calculations = tool_config.get("group_calculations", [])
                    keyword_to_col = tool_config.get("keyword_to_column", {})

                    for group in group_calculations:
                        try:
                            calculate_group_ratios(ws, next_row, group, keyword_to_col)
                        except Exception as e:
                            group_name = group.get("name", "Unknown")
                            print(f"【错误】分组计算失败 '{group_name}': {e}")

                # 动态边框：A 到当前行最后一个非空列
                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )

                max_col = 1
                for col_idx in range(1, ws.max_column + 1):
                    if ws.cell(row=next_row, column=col_idx).value is not None:
                        max_col = col_idx

                for col_idx in range(1, max_col + 1):
                    ws.cell(row=next_row, column=col_idx).border = thin_border

                print(f"【边框】第 {next_row} 行 A-{get_column_letter(max_col)} 已加边框")

                print(f"【完成】第 {next_row} 行: {sheet_name}")
                total_files_processed += len(matched_files)

        # --- 步骤6：保存结果 ---
        wb.save(temp_file.name)
        shutil.copy(temp_file.name, summary_path)
        os.remove(temp_file.name)

        return True, f"✅ 成功处理 {total_files_processed} 个文件！\n📊 结果已保存至：\n{summary_path}"

    except Exception as e:
        return False, f"❌ 处理失败：{str(e)}"


# ========== GUI 入口函数 ==========

def launch(parent_window=None):
    """启动 GUI 界面（供 main.py 调用）"""
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import ttk

    # ❌ 不要创建新的 Tk() 实例！
    # root = tk.Tk()
    # root.withdraw()

    exe_dir = get_exe_dir()
    DEFAULT_TEMPLATE = os.path.join(exe_dir, "template.xlsx")
    DEFAULT_CONFIG_FOLDER = os.path.join(exe_dir, "json")

    def run_script(meta_vars):
        folder_path = folder_var.get().strip()  # ✅ 改为使用 StringVar
        excel_path = excel_var.get().strip()  # ✅
        config_path = DEFAULT_CONFIG_FOLDER

        if not folder_path:
            messagebox.showwarning("警告", "请先选择包含 ZIP 文件的日志文件夹！", parent=window)
            return
        if not os.path.exists(folder_path):
            messagebox.showerror("错误", f"日志文件夹不存在：\n{folder_path}", parent=window)
            return
        if not os.path.exists(excel_path):
            messagebox.showerror("错误", f"Excel 模板文件不存在：\n{excel_path}", parent=window)
            return

        if not os.path.isdir(config_path):
            messagebox.showerror("错误", f"配置文件夹不存在！\n路径：{config_path}", parent=window)
            return

        json_files = [f for f in os.listdir(config_path) if f.lower().endswith('.json')]
        if not json_files:
            messagebox.showerror("错误", f"配置文件夹中未找到任何 .json 文件！\n路径：{config_path}", parent=window)
            return

        # ✅ 提取用户输入的元信息（按顺序 A~E）
        meta_values = [
            meta_vars["vendor"].get().strip(),
            meta_vars["pn"].get().strip(),
            meta_vars["controller"].get().strip(),
            meta_vars["flash"].get().strip(),
            meta_vars["capacity"].get().strip()
        ]

        success, msg = process_folder(folder_path, excel_path, config_path, meta_values)
        if success:
            messagebox.showinfo("成功", msg, parent=window)
        else:
            messagebox.showerror("失败", msg, parent=window)

    # ✅ 使用 Toplevel，父窗口为传入的 parent_window（主菜单窗口）
    window = tk.Toplevel(parent_window)
    window.title("竞品数据汇总")
    window.geometry("400x320")
    window.resizable(False, False)
    window.transient(parent_window)  # 模态依附
    window.grab_set()               # 模态锁定

    # 居中（相对于父窗口或屏幕）
    window.update_idletasks()
    if parent_window:
        x = parent_window.winfo_x() + (parent_window.winfo_width() - 400) // 2
        y = parent_window.winfo_y() + (parent_window.winfo_height() - 240) // 2
    else:
        x = (window.winfo_screenwidth() - 400) // 2
        y = (window.winfo_screenheight() - 240) // 2
    window.geometry(f"+{x}+{y}")

    # ====== GUI 布局（保持不变）======
    main_frame = tk.Frame(window)
    main_frame.pack(padx=18, pady=12, fill="both", expand=True)
    main_frame.columnconfigure(0, weight=1)

    folder_var = tk.StringVar()
    excel_var = tk.StringVar()
    meta_vars = {
        "vendor": tk.StringVar(),  # 厂商
        "pn": tk.StringVar(),  # PN
        "controller": tk.StringVar(),  # 主控
        "flash": tk.StringVar(),  # Flash
        "capacity": tk.StringVar()  # 容量
    }

    def create_path_row(parent, label_text, entry_var, browse_cmd, row):
        frame = tk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        frame.columnconfigure(1, weight=1)

        tk.Label(frame, text=label_text, width=10, anchor="e", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, padx=(0, 6)
        )
        entry = tk.Entry(frame, textvariable=entry_var, font=("Microsoft YaHei", 10))
        entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        if browse_cmd:
            tk.Button(frame, text="浏览", command=browse_cmd, font=("Microsoft YaHei", 9), width=6).grid(
                row=0, column=2
            )
        return entry

    # 原有两行
    folder_entry = create_path_row(main_frame, "日志文件夹：", folder_var,
                                   lambda: folder_var.set(filedialog.askdirectory(parent=window)), 0)
    excel_entry = create_path_row(main_frame, "原汇总Excel：", excel_var,
                                  lambda: excel_var.set(filedialog.askopenfilename(
                                      parent=window,
                                      filetypes=[("Excel 文件", "*.xlsx")]
                                  )), 1)

    # 新增5行元信息（无“浏览”按钮）
    meta_labels = [("厂商(可选)：", "vendor"), ("PN(可选)：", "pn"), ("主控(可选)：", "controller"),
                   ("Flash(可选)：", "flash"), ("容量(可选)：", "capacity")]
    for i, (label, key) in enumerate(meta_labels):
        create_path_row(main_frame, label, meta_vars[key], None, 2 + i)

    separator = ttk.Separator(main_frame, orient='horizontal')
    separator.grid(row=7, column=0, sticky="ew", pady=8)

    btn_frame = tk.Frame(main_frame)
    btn_frame.grid(row=8, column=0, pady=6)
    start_btn = tk.Button(
        btn_frame,
        text="开始汇总",
        command=lambda: run_script(meta_vars),  # 👈 传入 meta_vars
        bg="#4CAF50",
        fg="white",
        font=("Microsoft YaHei", 10, "bold"),
        width=28,
        height=1,
        relief="flat"
    )
    start_btn.pack()

    if os.path.exists(DEFAULT_TEMPLATE):
        excel_var.set(DEFAULT_TEMPLATE)