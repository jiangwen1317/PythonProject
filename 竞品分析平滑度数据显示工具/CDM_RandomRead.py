from multiprocessing.resource_sharer import stop
from re import T
import re
import pandas as pd
import os, sys
import openpyxl as op
from asyncio.windows_events import NULL
from runpy import run_path
import PySimpleGUI as sg
import matplotlib.pyplot as plt
import random
import glob
import openpyxl
import pickle
import pandas as pd
from pandas import Series,DataFrame
import mplcursors


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
 
#将excel文档转为csv文档 
def excel_to_csv(file,to_file):
    #read_excel中sheetname含义
    #default 0 返回多表使用sheetname=[0,1],若sheetname=None是返回全表 
    
    #read_excel中header含义
    #default 0 指定列名行，默认0，即取第一行，数据为列名行以下的数据 ，若数据不含列名，则设定 header = None
    file_excel=pd.read_excel(file, sheet_name=0, dtype = "str")
    # print(file_excel.shape[0])
    file_excel.to_csv(to_file, index=False)
    # 返回行数作为进度条的最大范围
    return file_excel.shape[0]


#CMDQ平滑度
class dataclass():
    def __init__(self):
      self.node = ""
      self.Condition = ""
      self.configuration = ""
      self.tempx = []
      self.temnowpy = []
      self.temsetpy = []

      self.R_512MB = []
      self.R_1GB = []
      self.R_2GB = []
      self.R_4GB = []
      self.R_ALL_Capacity = []

      self.R_512MB_1 = []
      self.R_1GB_1 = []
      self.R_2GB_1 = []
      self.R_4GB_1 = []
      self.R_ALL_Capacity_1 = []

      self.line = []
      self.MMC_Types = []

# 设置高亮的格式，线条颜色
highlight_kwargs = dict(
    # Only the kwargs corresponding to properties of the artist will be passed.
    # Line2D.
    color="#00ff7f",
    markeredgecolor="#00ff7f",
    linewidth=2,
    markeredgewidth=3,
    # PathCollection.
    facecolor="#00ff7f",
    edgecolor="#00ff7f",
)

if __name__=='__main__':

    template_Node = []
    MMC_Type = []
    Node_Cnt = 0
    Node_Index = 0

    layout = [
        # [sg.FileBrowse('文件选择', target='-GETFILE-',key='-GETFILE-', enable_events=True, file_types=(("ALL Files", "*.*"),))],
	    # [sg.Text('选择的文件是：'), sg.Text('', key='-TEXT-', size=(60, 1),background_color='white', text_color='red')],

        [sg.FileBrowse('选择节点对应名称表', target='-GETFILE-',key='-GETFILE-', enable_events=True, file_types=(("ALL Files", "*.*"),))],
        [sg.Text('选择的单文件是：'), sg.Text('', key='-TEXT-', size=(60, 1),background_color='white', text_color='red')],
        [sg.FolderBrowse('测试文件路径', target='-GFOLDER-', key='-GFOLDER-', enable_events=True)],
        [sg.Text('选择的测试文件路径是：'), sg.Text('', key='-TEXT3-', size=(60, 1), background_color='white', text_color='red')],
        [sg.Button('提交', pad=((500, 18), (0, 0))), sg.Exit('退出')]
    ]

    # 创建主窗口，设置窗口名，给窗口传入layout指明的组件
    window = sg.Window("CDM_RandomRead_V1.0.1", layout)
    run_path = NULL
    while True:
        # 读取事件和输入型组件的返回值,values返回值是一个字典
        event, values = window.read()
        # 控制台输出，便于调试
        # 点击x退出
        if event == sg.WIN_CLOSED or event == '退出':
            window.close()
            sys.exit(0)
            break
        # # 获取文件夹选择框框的返回值，并将之显示在文本框
        # if event == '-GETFILE-':
        #     window['-TEXT-'].update(values['-GETFILE-'])
        #
        #      = values['-GETFILE-']

        # 获取单文件选择框的输出并将文件的绝对路径更新到文本框显示
        if event == '-GETFILE-':
            window['-TEXT-'].update(values['-GETFILE-'])
            template_path = values['-GETFILE-']
            print("template_path:", template_path)
            # last_Path = os.path.basename(template_path)  # 先获取文件路径
            # print("last_Path:", last_Path)

         # 获取文件夹选择框框的返回值，并将之显示在文本框
        if event == '-GFOLDER-':
            window['-TEXT3-'].update(values['-GFOLDER-'])
            run_path = values['-GFOLDER-']
            print("run_path:", run_path)
            last_Path = os.path.basename(run_path)  # 先获取文件路径
            print("last_Path:", last_Path)

        if event == "提交":
            if run_path != NULL:
                # print(run_path)
                break
            else:
                window['-TEXT-'].update("文件路径不能为空")

    
    FilePath1 = run_path + "/" + 'new.xls'

    file_res = os.path.exists(FilePath1)
    if file_res != True:
        FileName = file_name(run_path,'.xlsx')
        print(FileName)
        FilePath = []
        workbook = openpyxl.Workbook()
        sheet_total = workbook.active
        sheet_total.append(['node','Condition', '512MB', '1GB', '2GB', '4GB', 'ALL_Capacity'])
        for x in FileName:
            Y = run_path +"/" + x + '.xlsx'
            print(Y)
            FilePath.append(Y)
            workbook_temp = openpyxl.load_workbook(Y)
            sheet = workbook_temp.active
            print(sheet.max_column)
            print(sheet.max_row)

            for row in sheet.iter_rows(min_row=2, min_col=1, max_col=sheet.max_column, max_row=sheet.max_row):
                row_data = [col.value for col in row]
                sheet_total.append(row_data)

            workbook.save(FilePath1)
            print("save new.xls OK")

        else:
            print("new.xls have exist")

    to_file = run_path + '\\result.csv'
    max_value = excel_to_csv(FilePath1, to_file)
    print("max_value:",max_value)

    template_file = run_path + '\\template.csv'
    excel_to_csv(template_path,template_file)

    # template_file = run_path + '/' + 'template.pkl'
    # max_value = excel_to_pkl(template_path, template_file)
    #csv_change_format(template_file)

    window.close()

    # layout = [[sg.Text('数据解析进度')],
    #       [sg.ProgressBar(max_value, orientation='h', size=(40, 20), key='progressbar')],
    #       [sg.Cancel("取消", pad=((290, 20), (0, 0)))]]
    #
    # window = sg.Window('执行进度', layout)
    #
    # # 根据key值获取到进度条
    # progress_bar = window['progressbar']

    f1 = open(template_file,"r+",encoding= 'utf-8')
    # b = pickle.load(f1)
    # print(b)

    f1.readline()

    with f1 as file_to_read:
        while True:
            lines = file_to_read.readline()  # 整行读取数据
            # print("lines",lines)
            if lines:
                node, MMC_Type1 = lines.split(",", 1)
                template_Node.append(node)
                MMC_Type.append(MMC_Type1)
            else:
                break
    f1.close()


    f = open(to_file,'r')

    # # f.readline()
    f.readline()

    key_val = dict()

    datalist = []

    cnt = 0

    with f as file_to_read:
        while True:
            lines = file_to_read.readline()                                 # 整行读取数据
            if lines:

                node, Condition, R_512MB, R_1GB, R_2GB, R_4GB, R_ALL_Capacity, Other = lines.split(",",7)

                if node:
                    print(node)
                    A = dataclass()
                    A.node = node

                Index_CNT = 0
                for x in template_Node:
                    if A.node in x:
                        A.MMC_Types = MMC_Type[Index_CNT]
                    Index_CNT += 1

                if Condition:
                    print(Condition)
                    A.Condition = Condition

                if (A.Condition == "SeqFill-Normal"):
                    if is_number(R_512MB):
                        A.R_512MB.append(int(R_512MB))

                    if is_number(R_1GB):
                        A.R_1GB.append(int(R_1GB))

                    if is_number(R_2GB):
                        A.R_2GB.append(int(R_2GB))

                    if is_number(R_4GB):
                        A.R_4GB.append(int(R_4GB))

                    if is_number(R_ALL_Capacity):
                        print(R_ALL_Capacity)
                        A.R_ALL_Capacity.append(int(R_ALL_Capacity))
                else:
                    if is_number(R_512MB):
                        A.R_512MB_1.append(int(R_512MB))

                    if is_number(R_1GB):
                        A.R_1GB_1.append(int(R_1GB))

                    if is_number(R_2GB):
                        A.R_2GB_1.append(int(R_2GB))

                    if is_number(R_4GB):
                        A.R_4GB_1.append(int(R_4GB))

                    if is_number(R_ALL_Capacity):
                        A.R_ALL_Capacity_1.append(int(R_ALL_Capacity))
                if node:
                        datalist.append(A)

            else:
                break

            # event, values = window.read(timeout=1)
            # if event == '取消' or event is None:
            #     window.close()
            #     sys.exit(0)
            #     break
            #
            # cnt += 1
            #
            # progress_bar.UpdateBar(cnt)

    f.close()

    # window.close()

    # 创建一个折线图

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 显示中文标签

    plt.rcParams['axes.unicode_minus'] = False

    #fig = plt.figure(figsize=(16,8),dpi=85)

    fig = plt.figure(figsize=(20, 9), dpi=85)

    # 创建1个表格，111代表创建1行1列，当前在1的位置
    bx = fig.add_subplot(1, 1, 1)


    # 给表的Y轴位置加上标签，rotation代表让文字横着展示，labelpad代表文字距表格多远了
    bx.set_ylabel('速度', rotation=0, labelpad=20)

    maxx = 0
    maxy = 0

    node_cnt = 0

    for data in datalist:
        if len(data.R_512MB) > maxx:
            maxx = len(data.R_512MB)
        if len(data.R_1GB) > maxx:
            maxx = len(data.R_1GB)
        if len(data.R_2GB) > maxx:
            maxx = len(data.R_2GB)
        if len(data.R_4GB) > maxx:
            maxx = len(data.R_4GB)
        if len(data.R_ALL_Capacity) > maxx:
            maxx = len(data.R_ALL_Capacity)

        if len(data.R_512MB_1) > maxx:
            maxx = len(data.R_512MB_1)
        if len(data.R_1GB_1) > maxx:
            maxx = len(data.R_1GB_1)
        if len(data.R_2GB_1) > maxx:
            maxx = len(data.R_2GB_1)
        if len(data.R_4GB_1) > maxx:
            maxx = len(data.R_4GB_1)
        if len(data.R_ALL_Capacity_1) > maxx:
            maxx = len(data.R_ALL_Capacity_1)

        if len(data.R_1GB) > maxy:
            maxy = max(data.R_1GB)
        if len(data.R_512MB) > maxy:
            maxy = max(data.R_512MB)
        if len(data.R_2GB) > maxy:
            maxy = max(data.R_2GB)
        if len(data.R_4GB) > maxy:
            maxy = max(data.R_4GB)
        if len(data.R_ALL_Capacity) > maxy:
            maxy = max(data.R_ALL_Capacity)

        if len(data.R_1GB_1) > maxy:
            maxy = max(data.R_1GB_1)
        if len(data.R_512MB_1) > maxy:
            maxy = max(data.R_512MB_1)
        if len(data.R_2GB_1) > maxy:
            maxy = max(data.R_2GB_1)
        if len(data.R_4GB_1) > maxy:
            maxy = max(data.R_4GB_1)
        if len(data.R_ALL_Capacity_1) > maxy:
            maxy = max(data.R_ALL_Capacity_1)

        node_cnt += 1

    print(maxx)
    print(maxy)
    print(node_cnt)

    colors = getColor(node_cnt)

    lastval = ""


    obsX = [x for x in range(len(datalist[0].R_512MB))]
    line = bx.plot(obsX, datalist[0].R_512MB, color = colors[0], label = datalist[0].MMC_Types)
    datalist[0].temnowpy = datalist[0].R_512MB
    datalist[0].line = line

    if (len(datalist) > 3 ):
        layout = [
            # 单选按钮元素
            [sg.Text(r'速度类型', pad=((0, 20), (0, 0))),
             sg.Combo(['全盘_R_512MB', '全盘_R_1GB', '全盘_R_2GB', '全盘_R_4GB', '全盘_R_ALL_Capacity',
                       '负载_R_512MB', '负载_R_1GB', '负载_R_2GB', '负载_R_4GB', '负载_R_ALL_Capacity'],
                      default_value='全盘_R_512MB', text_color='black')],
            [sg.Checkbox(datalist[0].MMC_Types, default=True), sg.Checkbox(datalist[1].MMC_Types, auto_size_text=True),
             sg.Checkbox(datalist[2].MMC_Types, auto_size_text=True)],
            [[sg.Checkbox(data.MMC_Types) for data in datalist[i:i + 3]] for i in range(3, len(datalist), 3)],
            [sg.Checkbox("ALL", key="all")],
            [sg.Text(r'调整缩放倍数：', pad=((10, 0), (17, 0))),
             sg.Slider(range=(1, 100), key='-SWITCH-', default_value=0, resolution=5, size=(26, 15), orientation='h',
                       font=('Helvetica', 10))],
            [sg.Button('确定', pad=((240, 20), (0, 0))), sg.Exit('退出')]
        ]

    else:

        layout = [
            # 单选按钮元素
            [sg.Text(r'速度类型', pad=((0, 20), (0, 0))),
             sg.Combo(['全盘_R_512MB', '全盘_R_1GB', '全盘_R_2GB', '全盘_R_4GB', '全盘_R_ALL_Capacity',
                       '负载_R_512MB', '负载_R_1GB', '负载_R_2GB', '负载_R_4GB', '负载_R_ALL_Capacity'],
                      default_value='全盘_R_512MB', text_color='black') ],
            [sg.Checkbox(datalist[0].MMC_Types, default=True)],
            [[sg.Checkbox(data.MMC_Types)] for data in datalist[1:]],

            [sg.Checkbox("ALL", key="all")],
            [sg.Text(r'调整缩放倍数：', pad=((10, 0), (17, 0))),
             sg.Slider(range=(1, 100), key='-SWITCH-', default_value=0, resolution=5, size=(26, 15), orientation='h',
                       font=('Helvetica', 10))],
            [sg.Button('确定', pad=((240, 20), (0, 0))), sg.Exit('退出')]
        ]

    # 创建主窗口，设置窗口名，给窗口传入layout指明的组件
    window = sg.Window('CDM_RandomRead_V1.0.1', layout)

    bx.set_xlim([0, maxx + 30])
    bx.set_ylim([0, maxy + 10])

    plt.title(last_Path + "-平滑度曲线")

    # plt.xlabel("X")

    # plt.ylabel("Y")

    last_val = 0

    last_flag = 0

    while True:

        plt.legend(bbox_to_anchor=(1.02, 1), loc=2, borderaxespad=0, frameon=False)

        maxy = 0
        maxx = 0

        for data in datalist:
            if ((not data.line) or (not len(data.tempx)) or (not len(data.temsetpy))):
                continue
            data.line[0].set_xdata(data.tempx)
            data.line[0].set_ydata(data.temsetpy)
            if max(data.tempx) > maxx:
                maxx = max(data.tempx)
            if max(data.temsetpy) > maxy:
                maxy = max(data.temsetpy)

        # 缩放时自动变化x轴范围，y轴的范围变化不大暂时保持不变
        if maxx and maxy:
            if last_val:
                maxx = maxx  + 15 // last_val + 1
            bx.set_xlim([0, maxx])
            bx.set_ylim([0, maxy + 10])

        #绘制网格
        #alpha表示调节网格透明度
        plt.grid(alpha=0.4)

        # 这个就是表的刷新时间了，以秒为单位
        plt.pause(0.1)

        mplcursors.cursor(highlight=True, highlight_kwargs=highlight_kwargs).connect("add")

        event, values = window.read()
        # 控制台输出，便于调试
        # print(event)
        print(values)

        # 点击x退出
        if event == sg.WIN_CLOSED or event == '退出':
            break
        if event == "确定":
            # print(lastval)
            if values["all"]:
                for i in range(1, len(datalist) + 1):
                    window[i].update(1)
                    values[i] = True
                    last_flag = 1
            elif (not values["all"]) and (last_flag):
                for i in range(1, len(datalist) + 1):
                    last_flag = 0
                    window[i].update(0)
                    values[i] = False

            if values != lastval:
                for data in datalist:
                    if not data.line:
                        continue
                    data.line[0].remove()
                    data.line = NULL

                if values[0] == '全盘_R_512MB' :
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_512MB))]
                            line = bx.plot(obsX, datalist[i].R_512MB, color = colors[i], label = datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_512MB
                            datalist[i].line = line

                elif values[0] == '全盘_R_1GB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_1GB))]
                            line = bx.plot(obsX, datalist[i].R_1GB, color = colors[i], label = datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_1GB
                            datalist[i].line = line

                elif values[0] == '全盘_R_2GB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_2GB))]
                            line = bx.plot(obsX, datalist[i].R_2GB, color = colors[i], label = datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_2GB
                            datalist[i].line = line

                elif values[0] == '全盘_R_4GB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_4GB))]
                            line = bx.plot(obsX, datalist[i].R_4GB, color = colors[i], label = datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_4GB
                            datalist[i].line = line

                elif values[0] == '全盘_R_ALL_Capacity':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_ALL_Capacity))]
                            line = bx.plot(obsX, datalist[i].R_ALL_Capacity, color=colors[i], label=datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_ALL_Capacity
                            datalist[i].line = line

                elif values[0] == '负载_R_512MB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_512MB_1))]
                            line = bx.plot(obsX, datalist[i].R_512MB_1, color=colors[i], label=datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_512MB_1
                            datalist[i].line = line

                elif values[0] == '负载_R_1GB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_1GB_1))]
                            line = bx.plot(obsX, datalist[i].R_1GB_1, color=colors[i], label=datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_1GB_1
                            datalist[i].line = line

                elif values[0] == '负载_R_2GB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_2GB_1))]
                            line = bx.plot(obsX, datalist[i].R_2GB_1, color=colors[i], label=datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_2GB_1
                            datalist[i].line = line

                elif values[0] == '负载_R_4GB':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_4GB_1))]
                            line = bx.plot(obsX, datalist[i].R_4GB_1, color=colors[i], label=datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_4GB_1
                            datalist[i].line = line

                elif values[0] == '负载_R_ALL_Capacity':
                    for i in range(node_cnt):
                        if values[i + 1] == True:
                            obsX = [x for x in range(len(datalist[i].R_ALL_Capacity_1))]
                            line = bx.plot(obsX, datalist[i].R_ALL_Capacity_1, color=colors[i],
                                           label=datalist[i].MMC_Types)
                            datalist[i].temnowpy = datalist[i].R_ALL_Capacity_1
                            datalist[i].line = line

            if values['-SWITCH-'] == 0:
                val = 1
            else:
                val = int(values['-SWITCH-'])
            if val:
                last_val = val
                for i in range(node_cnt):
                    if values[i + 1] == True:
                        datalist[i].tempx.clear()
                        datalist[i].temsetpy.clear()
                        for x in range(len(datalist[i].temnowpy) // val):
                            temp = 0
                            datalist[i].tempx.append(x)
                            for j in range(val):
                                if (0 == datalist[i].temnowpy[(x * val) + j]):
                                    datalist[i].temnowpy[(x * val) + j] = 1
                                temp += 1000 / (datalist[i].temnowpy[(x * val) + j])
                            tempvaly = val * 1000 / temp
                            datalist[i].temsetpy.append(tempvaly)

            lastval = values

    window.close()
    print("all program finish")

