from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import multiprocessing
import matplotlib.pyplot as plt
import zipfile
import GET_Data
import GET_Data_HD_Tune

# 全局变量
exceptionfilelist = []
exceptionfileinfolist = []
ReportFlag = 0
FILE = ""
NUM = 0
filename = ""
path = ""


def file_name(file_dir, source_type):
    """递归查找指定类型的文件，返回文件路径列表"""
    L = []
    bflag_null = 0
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == source_type:
                L.append(os.path.join(root, file))
                bflag_null = 1
    if bflag_null:
        return L
    else:
        return bflag_null


def Pop_Up_Window_0():
    """选择报告生成模式：从 log 生成或从 excel 生成"""
    global ReportFlag
    result = [False]

    def on_log():
        global ReportFlag
        ReportFlag = 2
        result[0] = True
        window.destroy()

    def on_excel():
        global ReportFlag
        ReportFlag = 3
        result[0] = True
        window.destroy()

    window = tk.Tk()
    window.title('基础竞品分析工具_2.1')
    window.geometry('450x100')

    frame = tk.Frame(window)
    frame.pack(expand=True)

    btn_log = tk.Button(frame, text='获取log生成报告', width=20, height=2, command=on_log)
    btn_log.pack(side=tk.LEFT, padx=10)

    btn_excel = tk.Button(frame, text='获取excel的文件生成报告', width=20, height=2, command=on_excel)
    btn_excel.pack(side=tk.LEFT, padx=10)

    window.protocol("WM_DELETE_WINDOW", lambda: (result.__setitem__(0, False), window.destroy()))
    window.mainloop()

    return result[0]


def Pop_Up_Window_1():
    """选择数据文件夹并输入样品数量"""
    global PerformaceFlag
    global EroorInfoFlag
    global ReportFlag
    global FILE
    global NUM

    window = tk.Tk()
    window.title('基础竞品分析工具_V1.1')
    window.geometry('550x250')

    folder_path = tk.StringVar()
    result = [False]

    # 文件夹选择
    frame1 = tk.Frame(window)
    frame1.pack(pady=10, padx=10, fill=tk.X)
    tk.Button(frame1, text='请选择你的文件路径', command=lambda: folder_path.set(
        filedialog.askdirectory() or folder_path.get())).pack(side=tk.LEFT)

    # 显示选择的路径
    frame2 = tk.Frame(window)
    frame2.pack(pady=5, padx=10, fill=tk.X)
    tk.Label(frame2, text='你选择数据库所在文件夹是：').pack(side=tk.LEFT)
    path_label = tk.Label(frame2, textvariable=folder_path, bg='white', fg='black',
                          anchor=tk.W, relief=tk.SUNKEN, width=50)
    path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # 样品数量输入
    frame3 = tk.Frame(window)
    frame3.pack(pady=10, padx=10)
    tk.Label(frame3, text='请输入测试的样品的数量：  ').pack(side=tk.LEFT)
    num_entry = tk.Entry(frame3, width=20)
    num_entry.pack(side=tk.LEFT)

    # 按钮
    frame4 = tk.Frame(window)
    frame4.pack(pady=10)

    def on_confirm():
        global FILE, NUM
        FILE = folder_path.get()
        NUM = num_entry.get()
        print(FILE)
        print("NUM", NUM)
        result[0] = True
        window.destroy()

    def on_exit():
        window.destroy()

    tk.Button(frame4, text='确定', command=on_confirm).pack(side=tk.LEFT, padx=10)
    tk.Button(frame4, text='退出', command=on_exit).pack(side=tk.LEFT, padx=10)

    window.protocol("WM_DELETE_WINDOW", on_exit)
    window.mainloop()

    return result[0]


def extract_nested_zips(start_dir, max_iterations=2):
    """递归解压嵌套ZIP文件（最多max_iterations轮），解压后删除原始压缩包"""
    print(f"【开始】深度觧压 {start_dir} 下的所有 ZIP 文件，并删除压缩包...")

    for iteration in range(1, max_iterations + 1):

        zip_files = [
            os.path.join(root, file)
            for root, _, files in os.walk(start_dir)
            for file in files
            if file.lower().endswith('.zip')
        ]

        if not zip_files:
            print(f"【完成】第 {iteration} 轮：未发现 ZIP 文件，停止觧压。")
            break

        print(f"【觧压】第 {iteration} 轮：发现 {len(zip_files)} 个 ZIP 文件...")
        extracted = False
        for zip_path in zip_files:
            try:
                # 删除空文件
                if os.stat(zip_path).st_size == 0:
                    os.remove(zip_path)
                    print(f"          已删除空文件: {os.path.basename(zip_path)}")
                    continue

                extract_dir = os.path.dirname(zip_path)
                base_name = os.path.basename(zip_path)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(extract_dir)
                print(f"          已觧压: {base_name}")
                os.remove(zip_path)
                print(f"          已删除: {base_name}")
                extracted = True
            except Exception as e:
                print(f"          觧压失败: {os.path.basename(zip_path)} - {e}")

        if not extracted:
            print(f"【完成】第 {iteration} 轮后无新文件觧压，结束。")
            break
    print("【清理】所有可觧压的 ZIP 文件已处理并删除。")


class Result():
    """存储单个样品的性能和功耗测试数据"""

    def __init__(self):
        self.Node = ""

        self.SEQ_VCC_Write = []
        self.SEQ_VCCQ_Write = []
        self.SEQ_Speed_Write = []
        self.SEQ_Power_Write = []

        self.Random_VCC_Write = []
        self.Random_VCCQ_Write = []
        self.Random_Speed_Write = []
        self.Random_Power_Write = []

        self.SEQ_VCC_Read = []
        self.SEQ_VCCQ_Read = []
        self.SEQ_Speed_Read = []
        self.SEQ_Power_Read = []

        self.Random_VCC_Read = []
        self.Random_VCCQ_Read = []
        self.Random_Speed_Read = []
        self.Random_Power_Read = []


def Get_the_data(filename, min_col, max_col):
    """从Excel中读取指定列范围的功耗和性能数据
    
    Args:
        filename: Excel文件路径
        min_col: 数据起始列
        max_col: 数据结束列
        
    Returns:
        list: 包含所有样品数据的列表
    """
    datalist = []  # 存储所有样品数据
    col_cnt = 0
    workbook = load_workbook(filename)

    sheet1 = workbook["功耗测试"]
    sheet2 = workbook["性能数据"]

    # 读取VCC/VCCQ功耗数据
    for col in sheet1.iter_cols(min_row=2, max_row=22, min_col=min_col, max_col=max_col):
        Result_A = Result()
        Result_A.Node = col[0].value
        print(111, Result_A.Node)
        Power_Cnt = 0

        for cell in col:
            Power_Cnt += 1
            if (Power_Cnt > 1):

                try:
                    value = cell.value.strip()
                except AttributeError as e:
                    value = cell.value
                print(value)

                if (Power_Cnt % 2 == 0):
                    if (Power_Cnt < 12):

                        Result_A.SEQ_VCC_Read.append(value)
                    else:
                        Result_A.Random_VCC_Read.append(value)
                else:
                    if (Power_Cnt < 12):
                        Result_A.SEQ_VCCQ_Read.append(value)
                    else:
                        Result_A.Random_VCCQ_Read.append(value)

        # 读性能
        for col in sheet2.iter_cols(min_row=2, max_row=12, min_col=min_col + col_cnt, max_col=min_col + col_cnt):
            Power_Cnt = 0
            for cell in col:
                Power_Cnt += 1
                if (Power_Cnt > 1):
                    try:
                        value = cell.value.strip()
                    except AttributeError as e:
                        value = cell.value

                    if (Power_Cnt < 7):
                        Result_A.SEQ_Speed_Read.append(value)
                    else:
                        Result_A.Random_Speed_Read.append(value)

        # 读取写功耗数据
        for col in sheet1.iter_cols(min_row=27, max_row=46, min_col=min_col + col_cnt, max_col=min_col + col_cnt):
            Power_Cnt = 0

            for cell in col:
                try:
                    value = cell.value.strip()
                except AttributeError as e:
                    value = cell.value

                if (Power_Cnt % 2 == 0):
                    if (Power_Cnt < 10):
                        Result_A.SEQ_VCC_Write.append(value)
                    else:
                        Result_A.Random_VCC_Write.append(value)
                else:
                    if (Power_Cnt < 10):
                        Result_A.SEQ_VCCQ_Write.append(value)
                    else:
                        Result_A.Random_VCCQ_Write.append(value)

                Power_Cnt += 1

        # 读取写性能数据
        for col in sheet2.iter_cols(min_row=15, max_row=24, min_col=min_col + col_cnt, max_col=min_col + col_cnt):
            Power_Cnt = 0
            for cell in col:
                Power_Cnt += 1
                try:
                    value = cell.value.strip()
                except AttributeError as e:
                    value = cell.value

                if (Power_Cnt < 6):
                    Result_A.SEQ_Speed_Write.append(value)
                else:
                    Result_A.Random_Speed_Write.append(value)

        col_cnt += 1
        print("SEQ_Speed_Read:", Result_A.SEQ_Speed_Read)
        print("SEQ_VCC_Read", Result_A.SEQ_VCC_Read)
        print("SEQ_VCCQ_Read", Result_A.SEQ_VCCQ_Read)
        print("SEQ_Speed_Write:", Result_A.SEQ_Speed_Write)
        print("SEQ_VCC_Write", Result_A.SEQ_VCC_Write)
        print("SEQ_VCCQ_Write", Result_A.SEQ_VCCQ_Write)

        print("Random_Speed_Read:", Result_A.Random_Speed_Read)
        print("Random_VCC_Read", Result_A.Random_VCC_Read)
        print("Random_VCCQ_Read", Result_A.Random_VCCQ_Read)
        print("Random_Speed_Write:", Result_A.Random_Speed_Write)
        print("Random_VCC_Write", Result_A.Random_VCC_Write)
        print("Random_VCCQ_Write", Result_A.Random_VCCQ_Write)
        datalist.append(Result_A)

    return datalist  # 返回所有样品数据


def Draw_a_scatter_plot_and_save_it_to_excel(filename, path, position, title, x, y, xlabel, ylabel, label,
                                             x_max, y_max, png_name, AccumulationFlag, SaveFlag):
    """绘制单线条功耗-性能关系图，保存PNG并返回图片信息
    
    Returns:
        dict: SaveFlag为True时返回图片信息；否则返回 None
    """
    # 设置X轴刻度（每20一个刻度）
    x_step = [i for i in range(int(x_max) + 50) if i % 20 == 0]

    plt.pause(0.1)
    if AccumulationFlag:
        plt.cla()

    # 设置中文显示支持
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    plt.title(title)
    plt.xlabel(xlabel, labelpad=10)
    plt.ylabel(ylabel, labelpad=10)
    plt.grid(alpha=0.4)
    plt.plot(x, y, label=label)
    plt.axis([0, x_max, 0, y_max])
    plt.xticks(x_step)
    plt.legend()

    # 保存图片并返回信息供批量插入
    if SaveFlag:
        png_path = path + '\\' + png_name + ".png"
        plt.savefig(png_path)
        print("图片已保存:", png_name)

        # 返回图片信息
        return {
            'png_path': png_path,
            'position': position
        }

    return None


def _generate_single_chart(config, filename, path, is_first_chart, images_info, datalist):
    """生成单个功耗分析图表（内部辅助函数）"""
    AccumulationFlag = 1 if is_first_chart else 1
    cnt = 0
    SaveFlag = 0

    for data in datalist:
        # 计算总功耗（VCCQ×1.8 + VCC×3.3）
        if config['power_calc']:
            vccq_field, vcc_field, power_field = config['power_fields']
            vccq_list = getattr(data, vccq_field)
            vcc_list = getattr(data, vcc_field)
            power_list = getattr(data, power_field)

            for i in range(len(vccq_list)):
                try:
                    power_value = float(vccq_list[i]) * 1.800 + float(vcc_list[i]) * 3.300
                    power_list.append(power_value)
                except TypeError:
                    power_list.append(0)

        speed_data = getattr(data, config['speed_field'])
        power_data = getattr(data, config['power_field'])

        # 计算坐标轴范围
        x_max = max(power_data) + config['x_offset']
        try:
            y_max = max(speed_data) + 200
        except TypeError:
            print("y1 is none ")
            return 1

        ylabel = "速度"
        xlabel = "总功耗（VCCQ X 1.8 + VCC X 3.3）" if config['power_calc'] else "功耗"
        label = data.Node
        title = config['title']
        png_name = config['title']

        # 打印调试信息（仅第一个图表）
        if is_first_chart and cnt == 0:
            print(speed_data)

        # 判断是否需要保存（最后一个样品时保存）
        cnt += 1
        if cnt >= len(datalist):
            SaveFlag = 1

        # 绘制图表，收集图片信息
        img_info = Draw_a_scatter_plot_and_save_it_to_excel(
            filename, path, config['position'], title,
            power_data, speed_data, xlabel, ylabel,
            label, x_max, y_max, png_name,
            AccumulationFlag, SaveFlag
        )

        # 收集图片信息供后续批量插入
        if img_info:
            images_info.append(img_info)

        AccumulationFlag = 0


def creat_line_chart(filename, path, data_min_Col, data_max_Col, datalist):
    """创建所有功耗分析曲线图（顺序/随机读写，VCC/VCCQ/总功耗）
    
    图表位置根据数据列数动态计算：
    - 第一组（顺序读写）：紧贴数据区域右侧，从第 10+NUM 列开始
    - 第二组（随机读写）：与第一组间隔5列
    - 每组内6个图表按 3列×2行 网格排列
    """
    from openpyxl.utils import get_column_letter

    print("filename", filename)
    print("path", path)

    # 动态计算图表起始列
    num_samples = data_max_Col - data_min_Col + 1  # 实际样品数
    seq_start_col = data_min_Col + num_samples     # 顺序组起始列（数据结束后）
    rand_start_col = seq_start_col + 5             # 随机组起始列（顺序组后间隔5列）

    # 每组6个图表竖直排列，行号与原布局一致
    chart_rows = [1, 25, 50, 75, 100, 125]
    seq_col_letter = get_column_letter(seq_start_col)
    rand_col_letter = get_column_letter(rand_start_col)

    # 生成顺序组和随机组的位置列表
    seq_positions = [f"{seq_col_letter}{row}" for row in chart_rows]
    rand_positions = [f"{rand_col_letter}{row}" for row in chart_rows]

    print(f"图表定位: 数据列J-{get_column_letter(data_max_Col)}, "
          f"顺序组从{seq_col_letter}列, "
          f"随机组从{rand_col_letter}列")

    # 图表配置：定义所有12个图表的参数
    chart_configs = [
        # 顺序读写（6个图表，位置动态计算）
        {
            'title': '顺序读总功耗分析曲线',
            'position': seq_positions[0],
            'power_calc': True,
            'power_fields': ('SEQ_VCCQ_Read', 'SEQ_VCC_Read', 'SEQ_Power_Read'),
            'speed_field': 'SEQ_Speed_Read',
            'power_field': 'SEQ_Power_Read',
            'x_offset': 100
        },
        {
            'title': '顺序写总功耗分析曲线',
            'position': seq_positions[1],
            'power_calc': True,
            'power_fields': ('SEQ_VCCQ_Write', 'SEQ_VCC_Write', 'SEQ_Power_Write'),
            'speed_field': 'SEQ_Speed_Write',
            'power_field': 'SEQ_Power_Write',
            'x_offset': 100
        },
        {
            'title': '顺序读VCC功耗分析曲线',
            'position': seq_positions[2],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'SEQ_Speed_Read',
            'power_field': 'SEQ_VCC_Read',
            'x_offset': 50
        },
        {
            'title': '顺序读VCCQ功耗分析曲线',
            'position': seq_positions[3],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'SEQ_Speed_Read',
            'power_field': 'SEQ_VCCQ_Read',
            'x_offset': 50
        },
        {
            'title': '顺序写VCC功耗分析曲线',
            'position': seq_positions[4],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'SEQ_Speed_Write',
            'power_field': 'SEQ_VCC_Write',
            'x_offset': 50
        },
        {
            'title': '顺序写功耗VCCQ分析曲线',
            'position': seq_positions[5],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'SEQ_Speed_Write',
            'power_field': 'SEQ_VCCQ_Write',
            'x_offset': 50
        },
        # 随机读写（6个图表，位置动态计算）
        {
            'title': '随机读总功耗分析曲线',
            'position': rand_positions[0],
            'power_calc': True,
            'power_fields': ('Random_VCCQ_Read', 'Random_VCC_Read', 'Random_Power_Read'),
            'speed_field': 'Random_Speed_Read',
            'power_field': 'Random_Power_Read',
            'x_offset': 100
        },
        {
            'title': '随机写总功耗分析曲线',
            'position': rand_positions[1],
            'power_calc': True,
            'power_fields': ('Random_VCCQ_Write', 'Random_VCC_Write', 'Random_Power_Write'),
            'speed_field': 'Random_Speed_Write',
            'power_field': 'Random_Power_Write',
            'x_offset': 100
        },
        {
            'title': '随机读VCC功耗分析曲线',
            'position': rand_positions[2],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'Random_Speed_Read',
            'power_field': 'Random_VCC_Read',
            'x_offset': 50
        },
        {
            'title': '随机读VCCQ功耗分析曲线',
            'position': rand_positions[3],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'Random_Speed_Read',
            'power_field': 'Random_VCCQ_Read',
            'x_offset': 50
        },
        {
            'title': '随机写VCC功耗分析曲线',
            'position': rand_positions[4],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'Random_Speed_Write',
            'power_field': 'Random_VCC_Write',
            'x_offset': 50
        },
        {
            'title': '随机写功耗VCCQ分析曲线',
            'position': rand_positions[5],
            'power_calc': False,
            'power_fields': None,
            'speed_field': 'Random_Speed_Write',
            'power_field': 'Random_VCCQ_Write',
            'x_offset': 50
        },
    ]

    # 执行所有图表生成，收集图片信息
    images_info = []  # 收集所有图片信息供批量插入

    for idx, config in enumerate(chart_configs):
        is_first_chart = 1 if idx == 0 else 0
        result = _generate_single_chart(config, filename, path, is_first_chart, images_info, datalist)
        if result == 1:
            return 1

    # 批量插入所有图表到Excel（仅一次文件IO）
    if images_info:
        print(f"\n开始批量插入{len(images_info)}个图表到Excel...")
        workbook = load_workbook(filename)
        ws = workbook["功耗测试"]

        for img_info in images_info:
            img = OpenpyxlImage(img_info['png_path'])
            ws.add_image(img, img_info['position'])

        workbook.save(filename)
        print("所有图表已成功插入Excel并保存！")


excel = "竞品分析基本测试项.xlsx"
excel1 = "竞品分析基本测试项模板.xlsx"

if __name__ == '__main__':
    multiprocessing.freeze_support()
    Pop_Up_Window_0()
    Pop_Up_Window_1()

    NUM = int(NUM)
    path = FILE + "/" + excel
    path1 = excel1
    data_min_Col = 10
    data_max_Col = NUM + data_min_Col - 1
    print(path)

    if (2 == ReportFlag):
        workbook = load_workbook(path1)
        workbook.save(path)

        # 统一解压所有ZIP文件（避免在子模块中重复觧压）
        FileZip = file_name(FILE, '.zip')
        if FileZip:
            print("找到的zip文件:", FileZip)
            extract_nested_zips(FILE, max_iterations=3)

        GET_Data.CDM_Speed_Collect(FILE, path, False)

    datalist = Get_the_data(path, data_min_Col, data_max_Col)
    creat_line_chart(path, FILE, data_min_Col, data_max_Col, datalist)

    # 调用HD Tune数据处理，获取实际列数（自动删除空列）
    actual_col_ida, actual_col_clean = GET_Data_HD_Tune.Speed_Collect(FILE, path, False, "平滑度曲线-IDA",
                                                                      "平滑度曲线-CLEAN")
    print(f"平滑度曲线实际样品数 - IDA: {actual_col_ida}, CLEAN: {actual_col_clean}")

    messagebox.showinfo('提示', '确认完成')
