# extraction_core 纯逻辑单元测试（不依赖 GUI / openpyxl）
import zipfile

import extraction_core


class TestExtractContentAfterKeyword:
    def test_last_only_returns_last_occurrence(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_text(
            "Max_Seq_Rd_Spd: 100.1\n"
            "other line\n"
            "Max_Seq_Rd_Spd: 266.7\n",
            encoding="utf-8",
        )
        assert extraction_core.extract_content_after_keyword(str(txt), "Max_Seq_Rd_Spd:") == "266.7"

    def test_extract_all_returns_ordered_list(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_text(
            "Spd: 1\nSpd: 2\nSpd: 3\n",
            encoding="utf-8",
        )
        assert extraction_core.extract_content_after_keyword(str(txt), "Spd:", last_only=False) == ["1", "2", "3"]

    def test_takes_last_comma_value(self, tmp_path):
        # 逗号分隔的多值取最后一个非空值
        txt = tmp_path / "log.txt"
        txt.write_text("Spd: 100, 200, 300,\n", encoding="utf-8")
        assert extraction_core.extract_content_after_keyword(str(txt), "Spd:") == "300"

    def test_missing_keyword_returns_none(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_text("nothing here\n", encoding="utf-8")
        assert extraction_core.extract_content_after_keyword(str(txt), "Spd:") is None
        assert extraction_core.extract_content_after_keyword(str(txt), "Spd:", last_only=False) is None

    def test_keyword_only_line_is_skipped(self, tmp_path):
        # 关键字后无内容的行不计入结果
        txt = tmp_path / "log.txt"
        txt.write_text("Spd:\nSpd: 5\n", encoding="utf-8")
        assert extraction_core.extract_content_after_keyword(str(txt), "Spd:") == "5"

    def test_gbk_encoded_file(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_bytes("Config_Name: 配置A\n".encode("gbk"))
        assert extraction_core.extract_content_after_keyword(str(txt), "Config_Name:") == "配置A"

    def test_nonexistent_file_returns_none(self, tmp_path):
        assert extraction_core.extract_content_after_keyword(str(tmp_path / "missing.txt"), "Spd:") is None


class TestExtractNestedZips:
    def test_extracts_and_removes_zip(self, tmp_path):
        zip_path = tmp_path / "data.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("inner.txt", "hello")

        extraction_core.extract_nested_zips(str(tmp_path))

        assert (tmp_path / "inner.txt").read_text() == "hello"
        assert not zip_path.exists()

    def test_nested_zip_extracted_in_second_round(self, tmp_path):
        # 内层 ZIP 打包进外层 ZIP，需两轮解压
        inner_zip_path = tmp_path / "inner.zip"
        with zipfile.ZipFile(inner_zip_path, "w") as z:
            z.writestr("deep.txt", "deep")
        outer_zip_path = tmp_path / "outer.zip"
        with zipfile.ZipFile(outer_zip_path, "w") as z:
            z.write(inner_zip_path, "inner.zip")
        inner_zip_path.unlink()

        extraction_core.extract_nested_zips(str(tmp_path))

        assert (tmp_path / "deep.txt").read_text() == "deep"
        assert not outer_zip_path.exists()

    def test_no_zip_files_is_noop(self, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        extraction_core.extract_nested_zips(str(tmp_path))
        assert (tmp_path / "a.txt").read_text() == "x"

    def test_corrupt_zip_is_kept(self, tmp_path):
        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_bytes(b"not a real zip")
        extraction_core.extract_nested_zips(str(tmp_path))
        # 解压失败时不删除文件，保留以便检查
        assert bad_zip.exists()


class TestGetConfigName:
    def test_config_name_keyword(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_text("Config_Name: IDA-CMDQ-HS400\n", encoding="utf-8")
        assert extraction_core.get_config_name(str(txt)) == "IDA-CMDQ-HS400"

    def test_device_config_name_fallback(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_text("Device_Config_Name       : cfg1\n", encoding="utf-8")
        assert extraction_core.get_config_name(str(txt)) == "cfg1"

    def test_no_keyword_returns_empty(self, tmp_path):
        txt = tmp_path / "log.txt"
        txt.write_text("nothing\n", encoding="utf-8")
        assert extraction_core.get_config_name(str(txt)) == ""


class TestBuildWideRows:
    def test_board_columns_in_first_seen_order(self):
        records = [
            ("BOARD002", "HD_Tune", "cfgA", "Spd:", "10"),
            ("BOARD001", "HD_Tune", "cfgA", "Spd:", "20"),
            ("BOARD002", "HD_Tune", "cfgA", "Spd:", "30"),
        ]
        board_columns, rows = extraction_core.build_wide_rows(records)
        assert board_columns == ["BOARD002", "BOARD001"]
        assert len(rows) == 1
        assert rows[0]["values"] == {"BOARD002": "30", "BOARD001": "20"}

    def test_later_file_overwrites_same_board(self):
        # 同一板子的同 (配置, 关键字)：后处理的文件覆盖先出现的值
        records = [
            ("B1", "CDM", "cfgA", "Spd:", "old"),
            ("B1", "CDM", "cfgA", "Spd:", "new"),
        ]
        _, rows = extraction_core.build_wide_rows(records)
        assert rows[0]["values"]["B1"] == "new"
        assert len(rows) == 1

    def test_row_order_follows_config_then_keyword_first_seen(self):
        records = [
            ("B1", "S1", "cfgB", "K1:", "1"),
            ("B1", "S1", "cfgA", "K2:", "2"),
            ("B1", "S1", "cfgA", "K1:", "3"),
        ]
        _, rows = extraction_core.build_wide_rows(records)
        assert [(r["config"], r["keyword"]) for r in rows] == [
            ("cfgB", "K1:"),
            ("cfgA", "K2:"),
            ("cfgA", "K1:"),
        ]

    def test_script_bound_to_config_and_blank_not_overwriting(self):
        records = [
            ("B1", "HD_Tune", "cfgA", "Spd:", "1"),
            ("B2", "", "cfgA", "Spd:", "2"),  # 空 script 不覆盖已记录值
        ]
        _, rows = extraction_core.build_wide_rows(records)
        assert rows[0]["script"] == "HD_Tune"

    def test_missing_board_leaves_cell_empty(self):
        records = [
            ("B1", "S1", "cfgA", "Spd:", "1"),
            ("B2", "S1", "cfgB", "Spd:", "2"),
        ]
        board_columns, rows = extraction_core.build_wide_rows(records)
        assert board_columns == ["B1", "B2"]
        # cfgA 行只有 B1 有值，B2 缺失时 values 不含该键（写入侧留空）
        assert "B2" not in rows[0]["values"]

    def test_empty_records(self):
        board_columns, rows = extraction_core.build_wide_rows([])
        assert board_columns == []
        assert rows == []
