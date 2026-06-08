#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序入口 —— 主菜单 + 功能调度
"""

import tkinter as tk
from tkinter import messagebox

# 静态导入两个功能模块（必须与本文件同目录）
import competitor_compare
import Data_Summarization


def launch_competitor_summary():
    try:
        Data_Summarization.launch()
    except Exception as e:
        messagebox.showerror("错误", f"启动汇总工具失败：\n{e}")


def launch_competitor_compare():
    try:
        competitor_compare.launch()
    except Exception as e:
        messagebox.showerror("错误", f"启动对比工具失败：\n{e}")


def show_main_menu():
    root = tk.Tk()
    root.title("竞品数据工具V1.2.1")
    root.geometry("400x250")
    root.resizable(False, False)

    # 居中窗口
    root.update_idletasks()  # 确保 geometry 生效
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(root, text="请选择功能：", font=("Arial", 12, "bold")).pack(pady=30)

    tk.Button(
        root,
        text="📊 竞品数据汇总",
        command=launch_competitor_summary,
        font=("Arial", 11),
        width=25,
        height=2,
        bg="#28a745",
        fg="white"
    ).pack(pady=10)

    tk.Button(
        root,
        text="🔍 竞品数据对比",
        command=launch_competitor_compare,
        font=("Arial", 11),
        width=25,
        height=2,
        bg="#007bff",
        fg="white"
    ).pack(pady=10)

    tk.Button(
        root,
        text="🚪 退出",
        command=root.quit,
        font=("Arial", 11),
        width=25,
        height=2,
        bg="#6c757d",
        fg="white"
    ).pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    show_main_menu()