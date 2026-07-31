# -*- coding: utf-8 -*-
"""监控脚本本体（test_monitor.py / node_monitor.py）的最小冒烟检查。

仅覆盖两层可机械验证的行为：
1. 模块可导入：第三方依赖（yaml/requests/schedule/playwright）以桩模块替代，
   桩内所有会产生副作用的入口（启动浏览器、HTTP 请求、定时调度）一经调用即抛错，
   机械保证导入过程不触发浏览器/网络副作用；
2. CLI 参数解析层：main() 能按命令行参数把配置路径与运行模式正确传给监控类
   （监控类被替换为记录桩，不加载配置、不登录、不启动浏览器）。

Playwright 页面交互、通知推送等运行时行为按项目约定不做单元测试，
改动这些路径时仍需按 AGENTS.md「门禁覆盖边界」用运行命令手动验证。
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent


def _fail_on_call(name):
    """返回一个一经调用即失败的桩函数，用于封死副作用入口"""
    def _raiser(*args, **kwargs):
        raise AssertionError(f"冒烟检查不允许调用 {name}（导入与 CLI 解析层不应触发浏览器/网络副作用）")
    return _raiser


def _install_third_party_stubs(monkeypatch):
    """把脚本顶层 import 的第三方依赖替换为桩模块（monkeypatch 会话后自动还原）"""
    yaml_stub = types.ModuleType("yaml")
    yaml_stub.safe_load = _fail_on_call("yaml.safe_load")

    requests_stub = types.ModuleType("requests")
    requests_stub.post = _fail_on_call("requests.post")

    schedule_stub = types.ModuleType("schedule")
    schedule_stub.every = _fail_on_call("schedule.every")
    schedule_stub.run_pending = _fail_on_call("schedule.run_pending")

    sync_api_stub = types.ModuleType("playwright.sync_api")
    sync_api_stub.sync_playwright = _fail_on_call("playwright.sync_api.sync_playwright")
    sync_api_stub.expect = _fail_on_call("playwright.sync_api.expect")
    sync_api_stub.Page = type("Page", (), {})
    sync_api_stub.Browser = type("Browser", (), {})
    playwright_stub = types.ModuleType("playwright")
    playwright_stub.sync_api = sync_api_stub

    stubs = {
        "yaml": yaml_stub,
        "requests": requests_stub,
        "schedule": schedule_stub,
        "playwright": playwright_stub,
        "playwright.sync_api": sync_api_stub,
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)


def _import_script(monkeypatch, script_name):
    """在依赖桩就位后，从文件路径导入监控脚本本体（不经过 sys.path 常规导入）"""
    _install_third_party_stubs(monkeypatch)
    module_name = f"_smoke_{script_name}"
    spec = importlib.util.spec_from_file_location(module_name, TOOL_DIR / f"{script_name}.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


# ---------- 导入层冒烟：可导入、入口存在、导入过程零副作用 ----------

@pytest.mark.parametrize("script_name, entry_class", [
    ("test_monitor", "TestSystemMonitor"),
    ("node_monitor", "NodeMonitor"),
])
def test_import_without_side_effects(monkeypatch, script_name, entry_class):
    # 若脚本顶层新增了浏览器/网络调用，桩会在 exec_module 阶段直接抛错使本用例失败
    module = _import_script(monkeypatch, script_name)
    assert callable(module.main)
    assert isinstance(getattr(module, entry_class), type)


# ---------- CLI 解析层冒烟：test_monitor.py ----------

def _run_test_monitor_main(monkeypatch, argv):
    module = _import_script(monkeypatch, "test_monitor")
    calls = {}

    class _Recorder:
        def __init__(self, config_path):
            calls["config"] = config_path

        def run_check(self):
            calls["mode"] = "once"

        def run_scheduler(self):
            calls["mode"] = "scheduler"

    monkeypatch.setattr(module, "TestSystemMonitor", _Recorder)
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    return calls


def test_test_monitor_cli_defaults_to_scheduler(monkeypatch):
    calls = _run_test_monitor_main(monkeypatch, ["test_monitor.py"])
    assert calls == {"config": "config.yaml", "mode": "scheduler"}


def test_test_monitor_cli_once_with_custom_config(monkeypatch):
    calls = _run_test_monitor_main(
        monkeypatch, ["test_monitor.py", "--once", "-c", "custom.yaml"]
    )
    assert calls == {"config": "custom.yaml", "mode": "once"}


# ---------- CLI 解析层冒烟：node_monitor.py ----------

def _run_node_monitor_main(monkeypatch, argv):
    module = _import_script(monkeypatch, "node_monitor")
    calls = {}

    class _Recorder:
        def __init__(self, config_path):
            calls["config"] = config_path

        def run(self, headless=True, debug_pause=False):
            calls["headless"] = headless
            calls["debug_pause"] = debug_pause

    monkeypatch.setattr(module, "NodeMonitor", _Recorder)
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    return calls


def test_node_monitor_cli_defaults(monkeypatch):
    calls = _run_node_monitor_main(monkeypatch, ["node_monitor.py"])
    assert calls == {"config": "config.yaml", "headless": True, "debug_pause": False}


def test_node_monitor_cli_visible_debug_with_custom_config(monkeypatch):
    calls = _run_node_monitor_main(
        monkeypatch, ["node_monitor.py", "--visible", "--debug", "-c", "custom.yaml"]
    )
    assert calls == {"config": "custom.yaml", "headless": False, "debug_pause": True}


# ---------- CLI 解析层冒烟：未知参数应被 argparse 拒绝并退出 ----------

@pytest.mark.parametrize("script_name", ["test_monitor", "node_monitor"])
def test_cli_rejects_unknown_argument(monkeypatch, script_name):
    module = _import_script(monkeypatch, script_name)
    monkeypatch.setattr(sys, "argv", [f"{script_name}.py", "--no-such-flag"])
    with pytest.raises(SystemExit) as exc_info:
        module.main()
    assert exc_info.value.code == 2
