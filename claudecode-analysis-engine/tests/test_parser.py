# -*- coding: utf-8 -*-
"""
src/parser.py 最小聚焦回归测试

以仓内样例日志 logs/RTMS_RTMSLOG_0.txt 为 fixture，
断言解析成功、全局字段提取、KV 指标提取与数值转换等关键结果；
并用合成日志片段回归 [Section] 头识别与 Cycles/Result 行处理。

测试全程使用内存数据库 (sqlite ':memory:')，不触碰仓内 emmc_analysis.db。
"""

import os

import pytest

from src.config import Config
from src.database import Database
from src.parser import LogParser

ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_LOG = os.path.join(ENGINE_DIR, "logs", "RTMS_RTMSLOG_0.txt")


@pytest.fixture()
def parser():
    """内存数据库 + 默认配置的解析器，避免任何磁盘副作用"""
    db = Database(db_path=":memory:", config=Config())
    try:
        yield LogParser(db=db, config=Config())
    finally:
        db.close()


@pytest.fixture()
def sample_result(parser):
    """解析仓内样例日志，供多个用例共享断言"""
    assert os.path.exists(SAMPLE_LOG), f"样例日志缺失: {SAMPLE_LOG}"
    return parser.parse_file(SAMPLE_LOG)


class TestParseSampleLog:
    """基于真实样例日志的回归断言"""

    def test_parse_success(self, sample_result):
        assert sample_result.success is True
        assert sample_result.summary.parse_status == "Success"
        assert sample_result.error_message == ""

    def test_global_info_extraction(self, sample_result):
        summary = sample_result.summary
        assert summary.device_name == "DM3720.012.13"
        assert summary.tool_version == "V1.0.19"
        # 头部 50 行内 bFWVersion[8] 覆盖 bFWVersion[64] 是当前既定行为
        assert summary.fw_version == "0x0001070200000000"
        assert summary.flash_id == "0x45434437383443334130434100000000"

    def test_cycles_and_result(self, sample_result):
        # 日志包含 Cycles:0 与 Cycles:1，取最后一次
        assert sample_result.summary.test_cycles == 1
        # 最后一个 Result 行为 Pass (CheckStackUsage)
        assert sample_result.summary.test_result == "Pass"

    def test_metrics_extraction(self, sample_result):
        metrics = {m.metric_key: m for m in sample_result.metrics}
        assert len(sample_result.metrics) == 158

        # 十六进制值自动转十进制
        tlc_free = metrics["wTLCFreeBlkNum"]
        assert tlc_free.raw_value == "0x014d"
        assert tlc_free.num_value == 333.0
        assert tlc_free.hex_value == "0x014d"

        # 普通浮点值
        assert metrics["WAI"].num_value == pytest.approx(11.98)
        # 普通整数值
        assert metrics["dwStackUsage"].num_value == 9.0

    def test_default_section(self, sample_result):
        # 样例日志使用 "Name:" 风格段头，不匹配 [Section] 正则，
        # 所有指标应归入默认 Section
        sections = {m.section for m in sample_result.metrics}
        assert sections == {"Start_of_test"}


class TestSectionRecognition:
    """[Section] 头识别与跳过逻辑（合成日志片段）"""

    def test_section_header_switch(self, parser, tmp_path):
        log_file = tmp_path / "synthetic.txt"
        log_file.write_text(
            "Device_Name              :TEST.001\n"
            "[Wear_Detection]\n"
            "    WAI                    :11.980\n"
            "Cycles:3\n"
            "[EmptyBlk_Detection]\n"
            "    dwFreeBlockCnt         :0x0\n"
            "    Result                 :Fail!\n",
            encoding="utf-8",
        )

        result = parser.parse_file(str(log_file))
        assert result.success is True
        assert result.summary.device_name == "TEST.001"
        assert result.summary.test_cycles == 3
        assert result.summary.test_result == "Fail"

        section_by_key = {m.metric_key: m.section for m in result.metrics}
        # Section 头之前的 KV 归入默认 Section
        assert section_by_key["Device_Name"] == "Start_of_test"
        # Section 头之后的 KV 归入对应 Section
        assert section_by_key["WAI"] == "Wear_Detection"
        assert section_by_key["dwFreeBlockCnt"] == "EmptyBlk_Detection"

    def test_skip_section_hex_dump(self, parser, tmp_path):
        log_file = tmp_path / "hexdump.txt"
        log_file.write_text(
            "[eMMC_EXT_CSD]\n"
            "Offset:  00 01 02 03\n"
            "...000:  00 11 22 33\n"
            "[Wear_Detection]\n"
            "    WAI                    :1.0\n",
            encoding="utf-8",
        )

        result = parser.parse_file(str(log_file))
        assert result.success is True

        keys = [m.metric_key for m in result.metrics]
        # Hex Dump 内容整体聚合为一条 HexDump 记录，不逐行提取 KV
        assert keys.count("HexDump") == 1
        assert "Offset" not in keys
        assert "WAI" in keys

        hex_metric = next(m for m in result.metrics if m.metric_key == "HexDump")
        assert hex_metric.section == "eMMC_EXT_CSD"
        assert "00 11 22 33" in hex_metric.str_value
