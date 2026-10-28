# -*- coding: utf-8 -*-
"""免测主流程的可复用回归验证入口（仓库内可发现，非 pytest 用例）。

背景：pytest 门禁只覆盖各工具的 *_core.py 纯逻辑层；本工具改动最热的
GET_Data_HD_Tune.py（平滑度曲线主流程 Speed_Collect）与 GET_Data.py
（CDM 汇总 CDM_Speed_Collect）属免测路径，"pytest 通过"不代表其未回归。
此脚本把改动前后的主流程输出做一次机械比对，作为这些路径的验证关口，
是原一次性 .verify_hdtune/ 脚手架沉淀下来的、可提交复用的版本。

原理（A/B 基线比对）：
  1. 取基线版（默认 git HEAD）与当前工作区版的 GET_Data_HD_Tune.py 源码；
  2. 各自在独立临时目录里，用同一份已提交的样例数据
     （tests/verify_data，随仓库分发，任何克隆均可复现）跑一遍
     Power_and_Performance.py 主流程对平滑度曲线的调用：
     复制模板 -> Speed_Collect(FILE, path, False, "平滑度曲线-IDA", "平滑度曲线-CLEAN")；
  3. 比对两版产出的中间产物 Performance.csv（逐字节）与 IDA/CLEAN 两个
     Sheet 的全部非空单元格（复用 data_core.diff_cell_maps）。

用法（在装有 pandas/openpyxl/tkinter 的解释器下运行，即该工具的运行环境）：
  python tests/verify_mainflow.py                 # 基线取 HEAD，比对当前工作区
  python tests/verify_mainflow.py --base HEAD~1   # 指定基线提交
退出码：0=一致(PASS，无回归)；2=存在差异(FAIL)；非 0 其它错误。

注意：本文件名不匹配 pytest 的 test_*.py / *_test.py 收集规则，不会被门禁收集，
只作为手动验证脚本运行（需要 GUI 依赖的第三方库，不适合放进 pytest 门禁）。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

# 避免 Windows 控制台 GBK 编码打印替换字符时报错
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 目录名为中文，无法作为常规包导入，按路径动态定位仓库与工具目录
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(TESTS_DIR)
REPO = os.path.dirname(TOOL)
# 便于 import data_core（复用抽离出的纯对比逻辑）
sys.path.insert(0, TOOL)
FIXTURE = os.path.join(TESTS_DIR, "verify_data")
TEMPLATE = os.path.join(TOOL, "竞品分析基本测试项模板.xlsx")
EXCEL_NAME = "竞品分析基本测试项.xlsx"
SHEETS = ["平滑度曲线-IDA", "平滑度曲线-CLEAN"]
MODULE_NAME = "GET_Data_HD_Tune.py"

RUNNER = '''# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"{moddir}")
import GET_Data_HD_Tune
FILE = r"{datadir}".replace("\\\\", "/")
path = FILE + "/" + "{excel}"
ida, clean = GET_Data_HD_Tune.Speed_Collect(
    FILE, path, False, "平滑度曲线-IDA", "平滑度曲线-CLEAN")
print("RESULT ida=%d clean=%d" % (ida, clean))
'''


def read_worktree_module():
    with open(os.path.join(TOOL, MODULE_NAME), "rb") as f:
        return f.read()


def read_base_module(base_ref):
    proc = subprocess.run(
        ["git", "show", f"{base_ref}:基础竞品分析工具/{MODULE_NAME}"],
        cwd=REPO, capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace")[-2000:])
        sys.exit(f"无法读取基线版 {MODULE_NAME}（ref={base_ref}）")
    return proc.stdout


def run_version(tag, module_bytes, root):
    """在独立临时目录中用样例数据跑指定版本的 Speed_Collect，返回产物路径。"""
    workdir = os.path.join(root, tag)
    datadir = os.path.join(workdir, "verify_data")
    shutil.copytree(FIXTURE, datadir)
    # 主流程会先把模板复制为目标报表
    shutil.copy(TEMPLATE, os.path.join(datadir, EXCEL_NAME))
    moddir = os.path.join(workdir, "mod")
    os.makedirs(moddir)
    with open(os.path.join(moddir, MODULE_NAME), "wb") as f:
        f.write(module_bytes)
    shutil.copy(os.path.join(TOOL, "data_core.py"), os.path.join(moddir, "data_core.py"))
    runner_path = os.path.join(workdir, "run.py")
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(RUNNER.format(moddir=moddir, datadir=datadir, excel=EXCEL_NAME))

    proc = subprocess.run([sys.executable, runner_path], cwd=workdir,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"===== [{tag}] exit={proc.returncode} =====")
    tail = proc.stdout.strip().splitlines()[-6:]
    print("\n".join(tail))
    if proc.returncode != 0:
        print(proc.stderr[-3000:])
        sys.exit(f"[{tag}] 版本运行失败")
    return os.path.join(datadir, EXCEL_NAME), os.path.join(workdir, "Performance.csv")


def sheet_cells(xlsx, sheet):
    from openpyxl import load_workbook
    wb = load_workbook(xlsx)
    ws = wb[sheet]
    return {(c.row, c.column): c.value for row in ws.iter_rows() for c in row
            if c.value is not None}


def main():
    parser = argparse.ArgumentParser(description="免测主流程 A/B 回归比对验证")
    parser.add_argument("--base", default="HEAD",
                        help="基线引用（默认 HEAD），比对当前工作区版与之的输出差异")
    args = parser.parse_args()

    import data_core  # 复用抽离出的纯对比逻辑

    base_bytes = read_base_module(args.base)
    work_bytes = read_worktree_module()

    root = tempfile.mkdtemp(prefix="verify_mainflow_")
    try:
        base_xlsx, base_csv = run_version("base", base_bytes, root)
        work_xlsx, work_csv = run_version("worktree", work_bytes, root)

        with open(base_csv, "rb") as f1, open(work_csv, "rb") as f2:
            csv_same = f1.read() == f2.read()
        print(f"Performance.csv 一致: {csv_same}")

        all_same = csv_same
        for sheet in SHEETS:
            a = sheet_cells(base_xlsx, sheet)
            b = sheet_cells(work_xlsx, sheet)
            diff = data_core.diff_cell_maps(a, b)
            all_same = all_same and diff["same"]
            print(f"Sheet[{sheet}] 单元格数 base={diff['count_a']} "
                  f"worktree={diff['count_b']} 一致: {diff['same']}"
                  + (f" 差异示例: {diff['diff_keys']}" if not diff["same"] else ""))

        print("VERIFY-RESULT:", "PASS" if all_same else "FAIL")
        sys.exit(0 if all_same else 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
