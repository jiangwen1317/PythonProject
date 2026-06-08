#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 竞品数据对比工具 —— 按PN码提取数据 + 自动填充对比模板 + 智能条件格式
📌 核心：提取 + 填充 + 原样复制格式 + 智能对比
📌 数值列 → 红黄绿色阶（越大越好）
📌 百分比列 → 蓝色数据条（区间分布，不比大小）
📌 文本列 → 无格式
📌 支持字符串百分比（"60.1%"）和小数百分比（0.601）
📌 智能识别列类型，支持不固定表头
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.utils import get_column_letter
from datetime import datetime
from openpyxl.styles import Alignment, Font, Border, Side


# ==================== 🧠 辅助函数 ====================

def find_first_empty_row(ws, col=1):
    """查找第一个未被合并且为空的安全写入行"""
    for row in range(1, 1001):
        cell = ws.cell(row=row, column=col)
        in_merged = any(
            merged.min_row <= row <= merged.max_row and
            merged.min_col <= col <= merged.max_col
            for merged in ws.merged_cells.ranges
        )
        if not in_merged and cell.value is None:
            return row
    return ws.max_row + 1


def is_number(value):
    """强化版数值判断：支持整数、浮点数、百分比、千分位、科学计数法"""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, str):
        s = value.strip().lstrip("'")
        if s.endswith('%'):
            s = s.rstrip('%')
        s = s.replace(',', '')
        try:
            float(s)
            return True
        except ValueError:
            return False
    return False


def is_percentage(cell_value, number_format=None):
    """严格判断是否为百分比格式"""
    if isinstance(cell_value, str):
        s = cell_value.strip().lstrip("'")
        if s.endswith('%'):
            clean = s.rstrip('%').replace(',', '').strip()
            if clean == '':
                return False
            try:
                float(clean)
                return True
            except ValueError:
                return False
    elif isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool):
        if number_format and '%' in number_format:
            return 0 <= cell_value <= 1
    return False


def _add_summary_row(ws, summary_row, end_col):
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # 1️⃣ 先合并 A-E
    ws.merge_cells(start_row=summary_row, start_column=1, end_row=summary_row, end_column=5)

    # 2️⃣ 设置“小结”文字（只在 A 列）
    title_cell = ws.cell(row=summary_row, column=1)
    title_cell.value = "小结"
    title_cell.font = Font(bold=True)  # 后续会被统一字体覆盖，这里可简化
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    # 3️⃣ 给整行（A 到 end_col）每个单元格加边框
    for col in range(1, end_col + 1):
        ws.cell(row=summary_row, column=col).border = border


def apply_uniform_font_to_workbook(workbook, font_name="Microsoft YaHei"):
    """
    遍历工作簿所有工作表，将所有非空或有样式的单元格字体名称统一为指定字体，
    保留字号、加粗、颜色等其他属性。
    """
    for ws in workbook.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                # 处理有内容 或 有样式的单元格（避免漏掉带格式的空表头）
                if cell.value is not None or cell.has_style:
                    current_font = cell.font or Font()
                    cell.font = Font(
                        name=font_name,
                        size=current_font.size,
                        bold=current_font.bold,
                        italic=current_font.italic,
                        underline=current_font.underline,
                        strike=current_font.strike,
                        color=current_font.color,
                        family=current_font.family,
                        scheme=current_font.scheme
                    )


# ==================== 🧩 核心处理函数 ====================

def extract_and_fill_by_pn(source_file, template_file, pn_list, output_path):
    """
    核心功能：按 PN 码提取数据 → 填入模板 → 原样复制格式 + 智能条件格式 + 追加小结行
    """
    wb = load_workbook(template_file)
    source_wb = load_workbook(source_file, data_only=False)

    total_filled = 0
    matched_sheets = []

    # 预定义条件格式规则（复用）
    color_scale_rule = ColorScaleRule(
        start_type='min', start_color='F8696B',
        mid_type='percentile', mid_value=50, mid_color='FFEB84',
        end_type='max', end_color='63BE7B'
    )

    for sheet_name in source_wb.sheetnames:
        if sheet_name not in wb.sheetnames:
            continue

        source_ws = source_wb[sheet_name]
        target_ws = wb[sheet_name]

        # 匹配 PN 码（B列 = 第2列）
        matched_rows = [
            row_idx for row_idx in range(1, source_ws.max_row + 1)
            if str(source_ws.cell(row=row_idx, column=2).value).strip() in pn_list
        ]

        if not matched_rows:
            continue

        # 找到模板中第一个安全写入行
        start_row = find_first_empty_row(target_ws, col=1)
        written_rows = []
        end_col = 1

        # 复制数据和格式
        for row_idx in matched_rows:
            current_end = 1
            for col_idx in range(1, source_ws.max_column + 1):
                src_cell = source_ws.cell(row=row_idx, column=col_idx)
                tgt_cell = target_ws.cell(row=start_row, column=col_idx)

                tgt_cell.value = src_cell.value

                if src_cell.has_style:
                    tgt_cell.number_format = src_cell.number_format
                    tgt_cell.font = src_cell.font.copy()
                    tgt_cell.border = src_cell.border.copy()
                    tgt_cell.fill = src_cell.fill.copy()
                    tgt_cell.alignment = src_cell.alignment.copy()
                    tgt_cell.protection = src_cell.protection.copy()

                if src_cell.value is not None:
                    current_end = col_idx

            end_col = max(end_col, current_end)
            written_rows.append(start_row)
            start_row += 1

        # 添加小结行
        _add_summary_row(target_ws, start_row, end_col)

        count = len(matched_rows)
        total_filled += count
        matched_sheets.append(f"{sheet_name}({count}行)")

        # 智能条件格式（仅当有 ≥2 行数据时应用）
        if len(written_rows) >= 2:
            min_row = min(written_rows)
            max_row = max(written_rows)

            for col_idx in range(1, target_ws.max_column + 1):
                values = []
                is_percent_col = False
                is_numeric_col = False

                for row in written_rows:
                    cell = target_ws.cell(row=row, column=col_idx)
                    cell_value = cell.value

                    if is_percentage(cell_value, cell.number_format):
                        is_percent_col = True
                        try:
                            if isinstance(cell_value, str):
                                clean_val = cell_value.strip().lstrip("'").rstrip('%').replace(',', '')
                                values.append(float(clean_val) / 100)
                            else:
                                values.append(float(cell_value))
                        except (ValueError, TypeError):
                            continue
                    elif is_number(cell_value):
                        is_numeric_col = True
                        try:
                            clean_val = str(cell_value).strip().lstrip("'").rstrip('%').replace(',', '')
                            values.append(float(clean_val))
                        except (ValueError, TypeError):
                            continue

                if len(values) < 2:
                    continue

                col_letter = get_column_letter(col_idx)
                range_str = f"{col_letter}{min_row}:{col_letter}{max_row}"

                if is_percent_col:
                    data_bar_rule = DataBarRule(
                        start_type='min', end_type='max',
                        color="638EC6", showValue=True
                    )
                    target_ws.conditional_formatting.add(range_str, data_bar_rule)
                elif is_numeric_col:
                    target_ws.conditional_formatting.add(range_str, color_scale_rule)

    if total_filled == 0:
        raise ValueError(f"未找到任何匹配的竞品PN码：{pn_list}")

    # ✅ 关键一步：统一整个工作簿字体为微软雅黑（保留其他样式）
    apply_uniform_font_to_workbook(wb, "微软雅黑")

    wb.save(output_path)
    return total_filled, matched_sheets


# ==================== 🖥️ GUI 启动器 ====================

def launch():
    root = tk.Tk()
    root.title("竞品数据对比")
    window_width = 580
    window_height = 260
    root.geometry(f"{window_width}x{window_height}")
    root.resizable(False, False)

    # ========== 居中窗口 ==========
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"+{x}+{y}")
    # =============================

    source_file = tk.StringVar()

    # 🔍 获取程序所在目录（兼容 .py 和 .exe）
    if getattr(sys, 'frozen', False):
        # 打包成 exe 时
        script_dir = os.path.dirname(sys.executable)
    else:
        # 正常运行 .py 时
        script_dir = os.path.dirname(os.path.abspath(__file__))

    DEFAULT_TEMPLATE = os.path.join(script_dir, "comparison.xlsx")

    if not os.path.exists(DEFAULT_TEMPLATE):
        exe_or_script = "程序" if getattr(sys, 'frozen', False) else "脚本"
        messagebox.showerror("模板缺失", f"未找到对比模板文件：\n{DEFAULT_TEMPLATE}\n\n请将 comparison.xlsx 放在 {exe_or_script} 所在目录！")
        root.destroy()
        return

    def select_source():
        f = filedialog.askopenfilename(title="选择竞品汇总数据源", filetypes=[("Excel文件", "*.xlsx")])
        if f:
            source_file.set(f)
            lbl_source.config(text=os.path.basename(f))

    def run_compare():
        source_path = source_file.get()
        pn_text = entry_pn.get().strip()

        if not source_path or not pn_text:
            messagebox.showwarning("输入不完整", "请选择竞品汇总数据并输入竞品PN码！")
            return

        try:
            pn_list = [p.strip() for p in pn_text.replace('，', ',').split(',') if p.strip()]
            if not pn_list:
                raise ValueError("请输入至少一个有效的竞品PN码")

            output_dir = os.path.dirname(source_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_name = f"竞品对比报告_{timestamp}.xlsx"
            output_path = os.path.join(output_dir, output_name)

            filled_count, matched_sheets = extract_and_fill_by_pn(
                source_path, DEFAULT_TEMPLATE, pn_list, output_path
            )

            summary = (
                f"✅ 成功提取 {len(pn_list)} 个竞品用于对比\n"
                f"📊 共填充 {filled_count} 行数据\n"
                f"📂 涉及表单：{', '.join(matched_sheets)}\n"
                f"\n💾 结果已保存至：\n{output_path}"
            )
            messagebox.showinfo("对比完成", summary)

        except Exception as e:
            messagebox.showerror("对比失败", f"操作过程中出现错误：\n{str(e)}")

    # === 文件选择区域 ===
    file_frame = tk.Frame(root)
    file_frame.pack(pady=8)

    row1 = tk.Frame(file_frame)
    row1.pack(fill="x", pady=2)
    tk.Button(row1, text="选择竞品汇总数据", command=select_source, width=18).pack(side="left", padx=(0, 8))
    lbl_source = tk.Label(row1, text="未选择", fg="gray", font=("Microsoft YaHei", 9))
    lbl_source.pack(side="left", fill="x", expand=True)

    # === PN码输入 ===
    tk.Label(root, text="输入竞品PN码（多个用逗号分隔）：", font=("Microsoft YaHei", 10)).pack(pady=(10, 3))
    entry_pn = tk.Entry(root, width=62, font=("Microsoft YaHei", 10))
    entry_pn.pack(pady=2)
    tk.Label(root, text="示例：ESG_2732_V1.5.0, KMDV6001DA-B425", fg="gray", font=("Microsoft YaHei", 8)).pack()

    # === 执行按钮 ===
    tk.Button(
        root,
        text="生成对比报告",
        command=run_compare,
        bg="#007bff",
        fg="white",
        font=("Microsoft YaHei", 10, "bold"),
        width=18,
        height=1
    ).pack(pady=14)

    root.after(100, lambda: entry_pn.focus_set())
    root.mainloop()


if __name__ == "__main__":
    launch()