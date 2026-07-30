# cdm_core 纯函数单元测试（不依赖 GUI / matplotlib / pandas）
import re

import cdm_core


class TestGetColor:
    def test_returns_n_colors(self):
        assert len(cdm_core.getColor(5)) == 5

    def test_colors_are_hex_format(self):
        # 每个分量取值范围 16~254，两位十六进制，格式为 #RRGGBB
        for color in cdm_core.getColor(10):
            assert re.fullmatch(r"#[0-9a-f]{6}", color)

    def test_zero_returns_empty(self):
        assert cdm_core.getColor(0) == []


class TestIsNumber:
    def test_integer_string(self):
        assert cdm_core.is_number("123") is True

    def test_negative_integer_string(self):
        assert cdm_core.is_number("-7") is True

    def test_float_string_is_not_int(self):
        # 原实现按 int() 判断，小数返回 False
        assert cdm_core.is_number("1.5") is False

    def test_non_numeric_string(self):
        assert cdm_core.is_number("abc") is False

    def test_empty_string(self):
        assert cdm_core.is_number("") is False


class TestFileName:
    def test_finds_matching_extension_without_ext(self, tmp_path):
        (tmp_path / "a.xlsx").write_text("x")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.xlsx").write_text("y")
        (sub / "c.txt").write_text("z")

        result = cdm_core.file_name(str(tmp_path), ".xlsx")

        # 返回的是不含扩展名的文件名
        assert sorted(result) == ["a", "b"]

    def test_no_match_returns_empty(self, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        assert cdm_core.file_name(str(tmp_path), ".xlsx") == []
