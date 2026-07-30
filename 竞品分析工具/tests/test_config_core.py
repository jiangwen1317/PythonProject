# config_core 纯逻辑单元测试（不依赖 GUI / openpyxl）
import json

import pytest

import config_core
from config_core import ConfigValidationError


class TestValidateSheetConfigs:
    def test_missing_sheet_raises_instead_of_silent_skip(self):
        # 核心用例：配置引用了模板中不存在的 sheet，必须报错中止而非静默跳过
        loaded = [("多路写入性能.json", [{"sheet_name": "多路写入性能", "tools": []}])]
        with pytest.raises(ConfigValidationError) as exc_info:
            config_core.validate_sheet_configs(loaded, ["封面", "读写Latency"])
        msg = str(exc_info.value)
        assert "多路写入性能.json" in msg
        assert "'多路写入性能' 在模板中不存在" in msg
        assert "读写Latency" in msg  # 报错信息需列出模板可用工作表

    def test_all_sheets_present_passes(self):
        loaded = [
            ("a.json", [{"sheet_name": "读写Latency"}]),
            ("b.json", [{"sheet_name": "上电Latency"}, {"sheet_name": "窗口测试"}]),
        ]
        # 不抛异常即通过
        config_core.validate_sheet_configs(loaded, ["读写Latency", "上电Latency", "窗口测试"])

    def test_collects_all_missing_entries(self):
        # 多个缺失项应一次性汇总报出，方便一次改齐
        loaded = [
            ("a.json", [{"sheet_name": "缺失1"}]),
            ("b.json", [{"sheet_name": "读写Latency"}, {"sheet_name": "缺失2"}]),
        ]
        with pytest.raises(ConfigValidationError) as exc_info:
            config_core.validate_sheet_configs(loaded, ["读写Latency"])
        msg = str(exc_info.value)
        assert "缺失1" in msg
        assert "缺失2" in msg

    def test_config_group_without_sheet_name_raises(self):
        # sheet_name 关键字段缺失同样必须报错，而非回落到默认值
        loaded = [("a.json", [{"tools": []}])]
        with pytest.raises(ConfigValidationError) as exc_info:
            config_core.validate_sheet_configs(loaded, ["读写Latency"])
        assert "未定义 sheet_name" in str(exc_info.value)


class TestLoadConfigFolder:
    def test_loads_sorted_json_files(self, tmp_path):
        (tmp_path / "b.json").write_text(
            json.dumps({"sheet_name": "B"}), encoding="utf-8"
        )
        (tmp_path / "a.json").write_text(
            json.dumps([{"sheet_name": "A1"}, {"sheet_name": "A2"}]), encoding="utf-8"
        )
        loaded = config_core.load_config_folder(str(tmp_path))
        assert [name for name, _ in loaded] == ["a.json", "b.json"]
        # dict / list 顶层结构均统一为配置组列表
        assert [g["sheet_name"] for g in loaded[0][1]] == ["A1", "A2"]
        assert [g["sheet_name"] for g in loaded[1][1]] == ["B"]

    def test_invalid_json_raises_instead_of_silent_skip(self, tmp_path):
        (tmp_path / "bad.json").write_text("{ not valid json", encoding="utf-8")
        with pytest.raises(ConfigValidationError) as exc_info:
            config_core.load_config_folder(str(tmp_path))
        assert "bad.json" in str(exc_info.value)

    def test_empty_folder_raises(self, tmp_path):
        with pytest.raises(ConfigValidationError):
            config_core.load_config_folder(str(tmp_path))

    def test_non_folder_path_raises(self, tmp_path):
        target = tmp_path / "not_a_folder.json"
        target.write_text("{}", encoding="utf-8")
        with pytest.raises(ConfigValidationError):
            config_core.load_config_folder(str(target))
