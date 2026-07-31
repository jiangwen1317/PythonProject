# monitor_core 纯逻辑单元测试（不依赖 playwright / requests / yaml）
from datetime import datetime

import pytest

import monitor_core
from monitor_core import ConfigValidationError, NodeCheckResult, NodeStatus, StepError


def _valid_task_config():
    return {
        "test_system": {"url": "http://x/", "username": "u", "password": "p"},
        "monitor": {
            "tasks": [
                {"task_id": "1", "task_name": "t1", "nodes": ["N1"]},
            ],
            "error_statuses": ["FAIL", "FATAL", "ERROR"],
        },
    }


def _valid_node_config():
    return {
        "test_system": {"url": "http://x/", "username": "u", "password": "p"},
        "monitor": {"nodes": ["DM3720.026.03"]},
    }


class TestValidateConfig:
    def test_valid_task_config_passes(self):
        monitor_core.validate_config(_valid_task_config(), mode="task")

    def test_valid_node_config_passes(self):
        monitor_core.validate_config(_valid_node_config(), mode="node")

    def test_non_dict_config_raises(self):
        with pytest.raises(ConfigValidationError):
            monitor_core.validate_config(None, mode="task")

    def test_unknown_mode_raises_value_error(self):
        with pytest.raises(ValueError):
            monitor_core.validate_config(_valid_task_config(), mode="xxx")

    def test_missing_test_system_field_reported(self):
        config = _valid_task_config()
        config["test_system"]["password"] = ""
        with pytest.raises(ConfigValidationError, match="test_system.password"):
            monitor_core.validate_config(config, mode="task")

    def test_task_mode_requires_tasks_and_error_statuses(self):
        config = _valid_node_config()  # 无 tasks / error_statuses
        with pytest.raises(ConfigValidationError) as exc_info:
            monitor_core.validate_config(config, mode="task")
        assert "monitor.tasks" in str(exc_info.value)
        assert "monitor.error_statuses" in str(exc_info.value)

    def test_task_missing_fields_all_collected(self):
        config = _valid_task_config()
        config["monitor"]["tasks"] = [{"task_id": "", "task_name": "t", "nodes": []}]
        with pytest.raises(ConfigValidationError) as exc_info:
            monitor_core.validate_config(config, mode="task")
        message = str(exc_info.value)
        assert "monitor.tasks[0].task_id" in message
        assert "monitor.tasks[0].nodes" in message

    def test_node_mode_requires_nodes(self):
        config = _valid_node_config()
        config["monitor"]["nodes"] = []
        with pytest.raises(ConfigValidationError, match="monitor.nodes"):
            monitor_core.validate_config(config, mode="node")


class TestIsErrorStatus:
    def test_default_error_statuses(self):
        assert monitor_core.is_error_status("FAIL") is True
        assert monitor_core.is_error_status("FATAL") is True
        assert monitor_core.is_error_status("ERROR") is True

    def test_normal_status_is_not_error(self):
        assert monitor_core.is_error_status("PASS") is False
        assert monitor_core.is_error_status("RUNNING") is False

    def test_custom_error_statuses(self):
        assert monitor_core.is_error_status("TIMEOUT", ["TIMEOUT"]) is True
        assert monitor_core.is_error_status("FAIL", ["TIMEOUT"]) is False


class TestIsRedStyle:
    def test_rgb_variants(self):
        assert monitor_core.is_red_style("color: rgb(255, 0, 0);") is True
        assert monitor_core.is_red_style("color:rgb(255,0,0)") is True

    def test_hex_and_named_variants(self):
        assert monitor_core.is_red_style("color: #FF0000") is True
        assert monitor_core.is_red_style("color: #f00") is True
        assert monitor_core.is_red_style("COLOR: RED") is True

    def test_non_red_or_empty(self):
        assert monitor_core.is_red_style("color: rgb(0, 128, 0);") is False
        assert monitor_core.is_red_style("") is False
        assert monitor_core.is_red_style(None) is False


class TestExtractStepNumber:
    def test_extracts_step(self):
        assert monitor_core.extract_step_number("步骤17 工具: CDM") == "步骤17"

    def test_first_match_wins(self):
        assert monitor_core.extract_step_number("步骤3\n步骤4") == "步骤3"

    def test_no_step_returns_empty(self):
        assert monitor_core.extract_step_number("没有编号") == ""
        assert monitor_core.extract_step_number("") == ""
        assert monitor_core.extract_step_number(None) == ""


class TestExtractToolName:
    def test_extracts_tool_name(self):
        assert monitor_core.extract_tool_name("工具: CDM 其他内容") == "CDM"

    def test_tool_name_without_space(self):
        assert monitor_core.extract_tool_name("工具:HDTune") == "HDTune"

    def test_no_tool_returns_empty(self):
        assert monitor_core.extract_tool_name("步骤17") == ""
        assert monitor_core.extract_tool_name("") == ""
        assert monitor_core.extract_tool_name("工具:") == ""


class TestBuildTaskUrl:
    def test_joins_base_url_and_task_id(self):
        assert monitor_core.build_task_url("http://x", "123") == "http://x/task/123"


class TestBuildDingtalkSignedUrl:
    def test_appends_timestamp_and_sign(self):
        url = monitor_core.build_dingtalk_signed_url(
            "http://x?access_token=t", "secret", timestamp_ms="1600000000000")
        # 钩住官方算法的确定性结果（固定 secret + 时间戳）
        assert url == (
            "http://x?access_token=t&timestamp=1600000000000"
            "&sign=XHSnLTbboLLBCrXfAQRHx6W9LkLB43RYwgcsOS2j3vs%3D"
        )

    def test_default_timestamp_produces_valid_shape(self):
        url = monitor_core.build_dingtalk_signed_url("http://x?access_token=t", "s")
        assert "&timestamp=" in url and "&sign=" in url


class TestParseNodeRow:
    def test_parses_full_row(self):
        cells = ["", "", " N1 ", "", "", "", " P1 ", " FAIL ", " 1.2.3.4 "]
        node = monitor_core.parse_node_row(cells)
        assert node == NodeStatus(name="N1", status="FAIL", project="P1", ip="1.2.3.4")

    def test_row_without_ip_column(self):
        cells = ["", "", "N1", "", "", "", "P1", "PASS"]
        node = monitor_core.parse_node_row(cells)
        assert node.ip == ""
        assert node.status == "PASS"

    def test_short_row_returns_none(self):
        assert monitor_core.parse_node_row(["a", "b", "c"]) is None
        assert monitor_core.parse_node_row([]) is None


def _node_result(name, status="PASS", errors=None):
    errors = errors or []
    return NodeCheckResult(
        node_name=name, task_name="", ip="", status=status,
        errors=errors, has_error=bool(errors))


class TestSummarizeResults:
    def test_counts_normal_error_not_found(self):
        results = [
            _node_result("N1"),
            _node_result("N2", status="FAIL",
                         errors=[StepError("步骤1", "CDM", "❌")]),
            _node_result("N3", status="NOT_FOUND"),
        ]
        assert monitor_core.summarize_results(results) == (1, 1, 1)

    def test_none_placeholder_not_counted_as_normal(self):
        # 检查失败占位 None：不计异常/未找到，但计入总数（与原 display_results 行为一致）
        assert monitor_core.summarize_results([None, _node_result("N1")]) == (2, 0, 0)

    def test_empty_results(self):
        assert monitor_core.summarize_results([]) == (0, 0, 0)


class TestFormatNodeResultsReport:
    def test_report_contains_counts_details_and_not_found(self):
        results = [
            _node_result("N1"),
            _node_result("N2", status="FAIL",
                         errors=[StepError("步骤17", "CDM", "❌")]),
            _node_result("N3", status="NOT_FOUND"),
        ]
        report = monitor_core.format_node_results_report(
            results, check_time=datetime(2026, 7, 31, 12, 0, 0))

        assert "节点监控检查结果" in report
        assert "检查时间: 2026-07-31 12:00:00" in report
        assert "检查节点数: 3" in report
        assert "正常节点: 1" in report
        assert "异常节点: 1" in report
        assert "未找到节点: 1" in report
        assert "❌ 节点: N2" in report
        assert "- 步骤17: CDM (❌)" in report
        assert "【未找到的节点】" in report
        assert "- N3" in report

    def test_no_error_sections_when_all_normal(self):
        report = monitor_core.format_node_results_report(
            [_node_result("N1")], check_time=datetime(2026, 7, 31, 12, 0, 0))
        assert "【异常节点详情】" not in report
        assert "【未找到的节点】" not in report


class TestFormatErrorMessage:
    def test_message_contains_node_fields_and_time(self):
        nodes = [
            NodeStatus(name="N1", status="FAIL", project="P1", ip="1.2.3.4",
                       details="步骤17: CDM"),
            NodeStatus(name="N2", status="FATAL", project="P2", ip="5.6.7.8"),
        ]
        fixed_time = datetime(2026, 7, 31, 12, 0, 0)

        message = monitor_core.format_error_message(nodes, check_time=fixed_time)

        assert "【测试系统告警】" in message
        assert "发现 2 个节点异常" in message
        assert "节点: N1" in message
        assert "详情: 步骤17: CDM" in message
        # 无 details 的节点不输出详情行
        assert message.count("详情:") == 1
        assert "检查时间: 2026-07-31 12:00:00" in message

    def test_empty_list_reports_zero(self):
        message = monitor_core.format_error_message(
            [], check_time=datetime(2026, 7, 31, 12, 0, 0))
        assert "发现 0 个节点异常" in message
