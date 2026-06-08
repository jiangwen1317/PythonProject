from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import ChartLines
import os
import re

import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image
from openpyxl.utils import get_column_letter
from openpyxl.styles import Border, Side


def file_name(file_dir, source_type):
    """递归查找指定后缀的所有文件
    
    Args:
        file_dir: 目录路径
        source_type: 文件后缀（如'.txt', '.zip'）
    
    Returns:
        list: 文件路径列表；若未找到则返回 0
    """
    file_list = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == source_type:
                file_list.append(os.path.join(root, file))

    return file_list if file_list else 0


def save_boardErrinfo(worksheet, cnt, col, get_buf):
    """写入数据到指定单元格，并返回下一列位置"""
    worksheet.cell(cnt, col).value = get_buf
    return col + 1


# 用户选择的数据文件夹路径
FILE = ""


def Pop_Up_Window_1():
    """显示文件夹选择对话框，结果存入全局变量 FILE"""
    global FILE

    window = tk.Tk()
    window.title('EVT性能数据汇总工具_V2.0.8')
    window.geometry('550x200')

    folder_path = tk.StringVar()

    # 文件夹选择
    frame1 = tk.Frame(window)
    frame1.pack(pady=10, padx=10, fill=tk.X)
    tk.Button(frame1, text='请选择你的文件路径', command=lambda: folder_path.set(
        filedialog.askdirectory() or folder_path.get())).pack(side=tk.LEFT)

    # 显示选择的路径
    frame2 = tk.Frame(window)
    frame2.pack(pady=5, padx=10, fill=tk.X)
    tk.Label(frame2, text='你选择数据库所在文件夹是：').pack(side=tk.LEFT)
    tk.Label(frame2, textvariable=folder_path, bg='white', fg='black',
             anchor=tk.W, relief=tk.SUNKEN, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # 按钮
    frame3 = tk.Frame(window)
    frame3.pack(pady=10)

    def on_confirm():
        global FILE
        FILE = folder_path.get()
        print(FILE)
        window.destroy()

    def on_exit():
        window.destroy()

    tk.Button(frame3, text='确认', command=on_confirm).pack(side=tk.LEFT, padx=10)
    tk.Button(frame3, text='退出', command=on_exit).pack(side=tk.LEFT, padx=10)

    window.protocol("WM_DELETE_WINDOW", on_exit)
    window.mainloop()


def process_fields(file_path, keys):
    """从测试文件中提取关键字段，汇总到Excel和CSV"""
    temp = ''
    lastfilepath = ""

    filename_txt = file_name(file_path, '.txt')
    if not filename_txt:
        return
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = '测试结果'

    # 节点去重：记录(boardID, Config_Name)对应的行号，重复时覆盖
    node_row_map = {}  # {(boardID, Config_Name): row_number}

    cnt = 0
    flag = 0

    for x in filename_txt:
        # 从路径反向解析：文件名\工具名\索引\板ID\路径
        try:
            filename, toolname, indx, boardID, filepath = x[::-1].split('\\', 4)
            lastfilepath = filepath
        except ValueError:
            filename, toolname, indx, boardID = x[::-1].split('\\', 3)
            filepath = lastfilepath

        toolname = toolname[::-1]
        boardID = "boardID:" + boardID[::-1]
        toolname_new = toolname

        col = 3

        if not ("CDM" in toolname_new or "H2" in toolname_new or "HD_Tune" in toolname_new):
            continue

        # 第一遍扫描：提取Config_Name用于去重判断
        config_name_for_check = toolname
        with open(x, 'rb') as f:
            line = f.readline()
            while line:
                try:
                    get_buf = line.decode('utf-8')
                except UnicodeDecodeError:
                    temp = ''
                    for bchar in line:
                        try:
                            temp += format(bchar, 'c')
                        except UnicodeDecodeError:
                            temp += ' '
                    get_buf = temp

                regex = re.compile("^Config_Name:")
                match = regex.match(get_buf)
                if match:
                    tool_configename = get_buf.split('.', 1)
                    config_name_for_check = tool_configename[0]
                    break
                line = f.readline()

        # 去重检查：如果重复则覆盖之前的行，否则新增行
        node_key = (boardID, config_name_for_check)
        if node_key in node_row_map:
            # 重复节点，使用之前的行号，覆盖旧数据
            prev_cnt = cnt  # 保存当前计数器，避免覆盖后影响后续新节点
            cnt = node_row_map[node_key]
            print(f"覆盖重复节点（保留最后一份）: {boardID} - {config_name_for_check} [行{cnt}]")
        else:
            # 新节点，分配新行号
            prev_cnt = None
            cnt += 1
            node_row_map[node_key] = cnt

        # 第二遍扫描：正式提取数据
        with open(x, 'rb') as f:
            line = f.readline()

            while line:
                # 尝试UTF-8解码，失败则逐字符转换
                try:
                    get_buf = line.decode('utf-8')
                except UnicodeDecodeError:
                    temp = ''
                    for bchar in line:
                        try:
                            temp += format(bchar, 'c')
                        except UnicodeDecodeError:
                            temp += ' '
                    get_buf = temp

                # 提取Config_Name作为工具配置名称
                regex = re.compile("^Config_Name:")
                match = regex.match(get_buf)
                if match:
                    if flag:
                        toolname_new = toolname
                    tool_configename = get_buf.split('.', 1)
                    toolname_new = tool_configename[0]
                    flag = 1

                # 匹配关键字并提取数据
                for key in keys:
                    key_pattern = '^' + key
                    regex = re.compile(key_pattern)
                    match = regex.match(get_buf)

                    if match:
                        if ',' in get_buf:
                            get_buf, _ = get_buf.split(",", 1)  # 取逗号前的值
                        get_buf = get_buf.strip()
                        col = save_boardErrinfo(worksheet, cnt, col, get_buf)

                line = f.readline()
        worksheet.cell(cnt, 1).value = boardID
        worksheet.cell(cnt, 2).value = toolname_new

        # 恢复计数器：覆盖操作后恢复原来的计数器值，避免下一个新节点行号错误
        if prev_cnt is not None:
            cnt = prev_cnt

    # 保存为Excel并导出CSV供后续处理
    excel_path = "Performance.xlsx"
    workbook.save(excel_path)
    df = pd.read_excel(excel_path)
    csv_file = 'Performance.csv'
    df.to_csv(csv_file, index=False)


def extract_key_value_pairs(input_string):
    """从字符串解析键值对（格式：key1:value1,key2:value2）"""
    pairs = input_string.split(',')
    result = {}
    for pair in pairs:
        key_value = pair.split(':')
        if len(key_value) == 2:
            result[key_value[0]] = key_value[1]
    return result


def extract_key(key_value_pairs, key):
    """安全提取指定键的值，不存在则返回 None"""
    try:
        return str(key_value_pairs[key])
    except KeyError:
        return None


def Write_To_EVT_Report_0(FILE, filename, Save_In_Work_Directory, SheetName1, SheetName2):
    """将Performance.csv中的HD Tune数据写入指定工作表，返回实际列数
    
    写数据固定写入行2-201（最多200个采样点），读数据固定从行202开始，
    确保写和读操作的数据分别独立处理，互不干扰。
    """
    template_file = r"Performance.csv"
    wb = load_workbook(filename)
    wb1 = wb[SheetName1]
    wb2 = wb[SheetName2]

    # 定义边框样式
    thin_side = Side(border_style="thin", color="000000")
    thin_border = Border(top=thin_side, left=thin_side, right=thin_side, bottom=thin_side)

    col_ida = 1
    col_clean = 1

    with open(template_file, 'r', encoding='utf-8') as f:
        line = f.readline()
        while line:
            key_value_pairs = extract_key_value_pairs(line)
            config_name = extract_key(key_value_pairs, 'Config_Name')

            # 仅处理HD Tune配置
            if config_name not in ["HD Tune-IDA", "CA-HD Tune-IDA",
                                    "HD Tune-CLEAN", "CA-HD Tune-CLEAN"]:
                line = f.readline()
                continue

            # 提取boardID用于第1行标题
            bid = extract_key(key_value_pairs, 'boardID')

            # 分离WriteSpeed和ReadSpeed段
            # CSV行格式：boardID:xxx,Config_Name:xxx,WriteSpeed:23,,WriteSpeed:23,,...,摘要字段,...,ReadSpeed:306,,...
            write_values = []  # 顺序写速度值
            read_values = []   # 顺序读速度值

            if "ReadSpeed:" in line:
                # 以ReadSpeed:为分界，前面是写数据段，后面是读数据段
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

            # 确定目标工作表和列号
            is_ida = config_name in ["HD Tune-IDA", "CA-HD Tune-IDA"]
            ws = wb1 if is_ida else wb2
            col = col_ida if is_ida else col_clean

            # 第1行写入boardID标题
            header_cell = ws.cell(row=1, column=col, value=bid if bid else "")
            header_cell.border = thin_border

            # 写数据：固定从第2行开始（最多200个采样点，行2-201）
            for i, val in enumerate(write_values[:200]):
                cell = ws.cell(row=i + 2, column=col, value=val)
                cell.border = thin_border

            # 读数据：固定从第202行开始
            for i, val in enumerate(read_values):
                cell = ws.cell(row=i + 202, column=col, value=val)
                cell.border = thin_border

            print(f"  {config_name}: 写{len(write_values)}点, 读{len(read_values)}点 → 列{col}")

            # 递增列号
            if is_ida:
                col_ida += 1
            else:
                col_clean += 1

            line = f.readline()

    # 实际写入的列数（减1是因为col_ida/col_clean从1开始，递增后是下一列）
    actual_col_ida = col_ida - 1
    actual_col_clean = col_clean - 1

    print(f"实际数据列数 - IDA: {actual_col_ida}, CLEAN: {actual_col_clean}")

    # 保存到目标文件夹
    folder_name = FILE.rpartition('\\')[2]
    output_filename = os.path.basename(filename)
    save_path = os.path.join(folder_name, output_filename)

    if Save_In_Work_Directory:
        wb.save(filename)
        print(save_path)

    wb.save(save_path)
    print("文件已保存至:", save_path)

    # 返回实际列数和保存路径供后续绘图使用
    return actual_col_ida, actual_col_clean, save_path


def Speed_Collect(FILE, filename, Save_In_Work_Directory, SheetName1, SheetName2):
    """主流程：提取HD Tune关键字段、写入工作表、动态绘图（觧压已在主模块完成）"""
    keys = ['WriteSpeed', 'ReadSpeed']
    print(f"关键字数量: {len(keys)}")

    process_fields(FILE, keys)
    actual_col_ida, actual_col_clean, saved_file_path = Write_To_EVT_Report_0(FILE, filename, Save_In_Work_Directory, SheetName1, SheetName2)
    
    print(f"数据写入完成，实际列数 - IDA: {actual_col_ida}, CLEAN: {actual_col_clean}")
    
    # 动态绘制图表（基于实际列数）
    # 已禁用：使用预设模板中的图表，不再通过代码动态生成，避免与模板图表冲突
    # if actual_col_ida > 0:
    #     print(f"开始绘制{SheetName1}曲线...")
    #     Draw_a_scatter(saved_file_path, FILE, SheetName1, actual_col_ida)
    # 
    # if actual_col_clean > 0:
    #     print(f"开始绘制{SheetName2}曲线...")
    #     Draw_a_scatter(saved_file_path, FILE, SheetName2, actual_col_clean)
    
    return actual_col_ida, actual_col_clean


def create_excel_native_chart(ws, title, data_start_row, data_end_row, 
                              data_start_col, data_end_col, chart_position):
    """创建 Excel 原生可编辑图表（用于平滑度曲线）
    
    Args:
        ws: 工作表对象
        title: 图表标题
        data_start_row: 实际数据起始行
        data_end_row: 数据结束行
        data_start_col: 数据起始列
        data_end_col: 数据结束列
        chart_position: 图表插入位置（如'N1'）
    """
    from openpyxl.chart import LineChart, Reference, Series
    from openpyxl.chart.axis import ChartLines
    chart = LineChart()
    chart.title = title
    chart.style = 2  # 使用样式2（与参考图一致）
    chart.y_axis.title = '速度 (MB/s)'
    chart.height = 15  # 增大高度
    chart.width = 28   # 增大宽度
    
    # 显示网格线（关键！）
    chart.y_axis.majorGridlines = ChartLines()
    
    # 确保显示坐标轴（关键配置）
    chart.x_axis.delete = False  # 确保X轴显示
    chart.y_axis.delete = False  # 确保Y轴显示
    
    # 定义Y轴数据范围（仅包含数据，不选表头）
    data_ref = Reference(ws, min_col=data_start_col, min_row=data_start_row, 
                         max_col=data_end_col, max_row=data_end_row)
    
    # 添加数据系列，不从数据中取标题
    chart.add_data(data_ref, titles_from_data=False)
    
    # 手动设置每个系列的标题（直接从第1行提取板卡名称，并关联到单元格）
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.data_source import StrRef
    for i, col_idx in enumerate(range(data_start_col, data_end_col + 1)):
        try:
            if i < len(chart.series):
                series = chart.series[i]
                # 获取第一行的单元格引用，确保图表可编辑且同步更新
                title_cell = ws.cell(row=1, column=col_idx)
                cell_ref = f"'{ws.title}'!{title_cell.coordinate}"
                series.title = SeriesLabel(strRef=StrRef(f=cell_ref))
        except (IndexError, AttributeError):
            continue
    
    # 配置图例在右侧，且不叠加在绘图区上方（自动挤压绘图区为图例留出空间）
    chart.legend.position = 'r'
    try:
        chart.legend.overlay = False
    except AttributeError:
        pass  # 部分openpyxl版本不支持overlay属性
    
    # 设置X轴为数值轴（避免竖条纹）
    chart.x_axis.scaling.min = 1
    chart.x_axis.scaling.max = data_end_row - data_start_row + 1
    
    # 设置Y轴从0开始，避免小波动显得过大
    chart.y_axis.scaling.min = 0
    
    # 显示坐标轴刻度线
    chart.x_axis.tickLblPos = 'low'  # X轴刻度标签位置
    chart.y_axis.tickLblPos = 'low'  # Y轴刻度标签位置
    
    # 插入图表
    ws.add_chart(chart, chart_position)
    print(f"已插入Excel原生图表: {title}，已关联第1行标题")


def Draw_a_scatter(filename, FILE, SheetName, num):
    """绘制HD Tune写入/读取性能曲线（IDA和CLEAN配置）
    
    Args:
        filename: Excel文件完整路径
        FILE: 图片保存路径
        SheetName: 工作表名称
        num: 实际列数
    """
    workbook = load_workbook(filename)
    ws = workbook[SheetName]
    
    # 获取实际数据行数
    total_rows = ws.max_row
    
    if total_rows < 3:
        print(f"警告：{SheetName} 数据不足")
        return

    is_ida_sheet = "IDA" in SheetName
    chart_prefix = "HD_Tune-IDA" if is_ida_sheet else "HD_Tune-Clean"

    # 动态计算图表起始列（数据列数 + 2）
    # 比如 3 列数据，图表从第 5 列开始
    chart_col_letter = get_column_letter(num + 2)

    # 第 1 个图：顺序写（固定为第 2 行到第 201 行）
    # 确保 200 个采样点全部划入顺序写
    write_end_row = 201
    
    # 如果总行数还没到 201，则取实际最大行
    if total_rows < 201:
        write_end_row = total_rows
    
    # 平滑度曲线使用Excel原生图表（可编辑）
    create_excel_native_chart(
        ws,
        f"{chart_prefix}顺序写分析曲线",
        data_start_row=2,        # 数据从第2行开始
        data_end_row=write_end_row,
        data_start_col=1,
        data_end_col=num,
        chart_position=f"{chart_col_letter}1"
    )

    # 第 2 个图：顺序读（从第 202 行开始）
    read_start_row = 202
    if total_rows < read_start_row:
        workbook.save(filename)
        return
    
    create_excel_native_chart(
        ws,
        f"{chart_prefix}顺序读分析曲线",
        data_start_row=read_start_row, 
        data_end_row=total_rows,
        data_start_col=1,
        data_end_col=num,
        chart_position=f"{chart_col_letter}30"
    )
    
    workbook.save(filename)
    print(f"{SheetName} 图表创建完成")


excel = "竞品分析基本测试项.xlsx"

if __name__ == '__main__':
    Pop_Up_Window_1()

    filename = excel
    path = FILE + "/" + filename
    print("文件路径:", FILE, path)

    Draw_a_scatter(path, FILE, "平滑度曲线-IDA", 1)

    messagebox.showinfo('提示', '确认完成')
