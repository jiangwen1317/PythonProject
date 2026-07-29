# data_core 纯函数单元测试（不依赖 GUI / pandas / openpyxl）
import os

import pytest

import data_core


class TestFindFiles:
    def test_finds_matching_extension_recursively(self, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("y")
        (sub / "c.log").write_text("z")

        result = data_core.find_files(str(tmp_path), '.txt')

        assert sorted(os.path.basename(p) for p in result) == ["a.txt", "b.txt"]

    def test_returns_empty_list_when_no_match(self, tmp_path):
        assert data_core.find_files(str(tmp_path), '.txt') == []


class TestDecodeLogLine:
    def test_utf8_line(self):
        assert data_core.decode_log_line("Max_Seq_Rd_Spd:266.7\n".encode('utf-8')) == "Max_Seq_Rd_Spd:266.7\n"

    def test_non_utf8_bytes_fall_back_to_char_conversion(self):
        # GBK 编码的中文无法按 UTF-8 解码，走逐字符转换分支
        raw = "值:1".encode('gbk')
        result = data_core.decode_log_line(raw)
        assert isinstance(result, str)
        assert result.endswith(":1")


class TestParseTxtPath:
    def test_full_path_layers(self):
        # 路径约定：...\板ID\索引\工具名\文件名
        txt = r"D:\data\DM3720.010.08\1\CDM-CA\log_Filter.txt"
        toolname, board_id, filepath = data_core.parse_txt_path(txt)
        assert toolname == "CDM-CA"
        assert board_id == "boardID:DM3720.010.08"
        assert filepath == r"D:\data"

    def test_short_path_uses_lastfilepath(self):
        txt = r"DM3720\1\HD_Tune\log.txt"
        toolname, board_id, filepath = data_core.parse_txt_path(txt, lastfilepath=r"D:\prev")
        assert toolname == "HD_Tune"
        assert board_id == "boardID:DM3720"
        assert filepath == r"D:\prev"


class TestExtractConfigName:
    def test_strips_after_first_dot(self):
        assert data_core.extract_config_name("Config_Name:IDA-CMDQ-HS400.suffix\n") == "Config_Name:IDA-CMDQ-HS400"

    def test_no_dot_returns_whole(self):
        assert data_core.extract_config_name("Config_Name:HS200") == "Config_Name:HS200"


class TestCleanMatchedValue:
    def test_takes_value_before_comma_and_strips(self):
        assert data_core.clean_matched_value("Max_Seq_Rd_Spd:266.7,unit:MB/s\n") == "Max_Seq_Rd_Spd:266.7"

    def test_no_comma_only_strips(self):
        assert data_core.clean_matched_value("  Sleep_Cur_VCC_Avg:0.12  \n") == "Sleep_Cur_VCC_Avg:0.12"


class TestExtractKeyValuePairs:
    def test_typical_csv_line(self):
        line = "boardID:3,Config_Name:IDA-CMDQ-HS400,Max_Seq_Rd_Spd:266.7"
        result = data_core.extract_key_value_pairs(line)
        assert result == {
            "boardID": "3",
            "Config_Name": "IDA-CMDQ-HS400",
            "Max_Seq_Rd_Spd": "266.7",
        }

    def test_malformed_pairs_are_skipped(self):
        # 无冒号或多个冒号的片段不进入结果
        result = data_core.extract_key_value_pairs("a:1,badpair,b:2:3")
        assert result == {"a": "1"}


class TestExtractKey:
    def test_existing_key(self):
        assert data_core.extract_key({"boardID": 3}, "boardID") == "3"

    def test_missing_key_returns_none(self):
        assert data_core.extract_key({}, "boardID") is None


class TestNormalizeCellValue:
    @pytest.mark.parametrize("value", [None, "", "NULL"])
    def test_empty_like_values_become_none(self, value):
        assert data_core.normalize_cell_value(value) is None

    def test_numeric_string_becomes_float(self):
        assert data_core.normalize_cell_value("266.7") == 266.7

    def test_non_numeric_string_kept_as_str(self):
        assert data_core.normalize_cell_value("HS400") == "HS400"
