"""
规则引擎单元测试

作者: QA Team
职责: 测试 rule_engine.py 的各项功能
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

from src.rules.rule_engine import RuleEngine
from src.rules.rule_parser import RuleParser


class TestRuleParser:
    """测试规则解析器"""

    def test_parse_threshold_condition(self):
        """测试解析阈值条件"""
        parser = RuleParser()
        
        condition = {
            "type": "threshold",
            "metric": "DO",
            "operator": "<",
            "threshold": 2.0
        }
        
        func = parser.compile_condition(condition)
        
        # 测试触发
        assert func({"DO": 1.5}) is True
        # 测试不触发
        assert func({"DO": 3.0}) is False

    def test_parse_duration_condition(self):
        """测试解析持续时间条件"""
        parser = RuleParser()
        
        condition = {
            "type": "duration",
            "metric": "DO",
            "operator": "<",
            "threshold": 2.0,
            "duration_minutes": 10
        }
        
        func = parser.compile_condition(condition)
        
        # 模拟历史数据
        data = {
            "DO": 1.5,
            "_history": {
                "DO": [1.5] * 20  # 持续20个周期低DO
            }
        }
        
        assert func(data) is True

    def test_parse_logic_condition(self):
        """测试解析逻辑组合条件"""
        parser = RuleParser()
        
        condition = {
            "type": "logic",
            "operator": "AND",
            "conditions": [
                {"type": "threshold", "metric": "Pump_Status", "operator": "==", "threshold": 1},
                {"type": "threshold", "metric": "Flow", "operator": "==", "threshold": 0}
            ]
        }
        
        func = parser.compile_condition(condition)
        
        # 泵运行但流量为0 (空转)
        assert func({"Pump_Status": 1, "Flow": 0}) is True
        # 泵运行且流量正常
        assert func({"Pump_Status": 1, "Flow": 10}) is False

    def test_parse_rate_of_change_condition(self):
        """测试解析变化率条件"""
        parser = RuleParser()
        
        condition = {
            "type": "rate_of_change",
            "metric": "Temperature",
            "window_minutes": 5,
            "min_change": 10
        }
        
        func = parser.compile_condition(condition)
        
        # 5分钟内升温12度
        data = {
            "Temperature": 52,
            "_history": {
                "Temperature": [40] * 10
            }
        }
        
        assert func(data) is True


class TestRuleEngine:
    """测试规则引擎"""
    
    @pytest.fixture
    def rule_engine(self, tmp_path):
        """创建规则引擎实例"""
        # 创建临时规则文件
        rules = {
            "rules": [
                {
                    "rule_id": "RULE_001",
                    "name": "缺氧异常",
                    "description": "溶解氧过低",
                    "enabled": True,
                    "severity": "critical",
                    "condition": {
                        "type": "threshold",
                        "metric": "DO",
                        "operator": "<",
                        "threshold": 2.0
                    },
                    "suggested_actions": ["增加曝气量"]
                }
            ]
        }
        
        rules_file = tmp_path / "test_rules.json"
        with open(rules_file, 'w') as f:
            json.dump(rules, f)
        
        return RuleEngine(str(rules_file))

    def test_load_rules(self, rule_engine):
        """测试加载规则"""
        assert len(rule_engine.rules) == 1
        assert rule_engine.rules[0]["rule_id"] == "RULE_001"

    def test_evaluate_single_rule(self, rule_engine):
        """测试评估单条规则"""
        # 触发规则的数据
        data = {"DO": 1.5}
        alerts = rule_engine.evaluate(data)
        
        assert len(alerts) == 1
        assert alerts[0]["rule_id"] == "RULE_001"
        assert alerts[0]["severity"] == "critical"

    def test_evaluate_no_alert(self, rule_engine):
        """测试不触发告警的情况"""
        # 正常数据
        data = {"DO": 3.0}
        alerts = rule_engine.evaluate(data)
        
        assert len(alerts) == 0

    def test_alert_suppression(self, rule_engine):
        """测试告警抑制"""
        data = {"DO": 1.5}
        
        # 第一次触发
        alerts1 = rule_engine.evaluate(data)
        assert len(alerts1) == 1
        
        # 短时间内再次触发 (应被抑制)
        alerts2 = rule_engine.evaluate(data)
        assert len(alerts2) == 0

    def test_get_statistics(self, rule_engine):
        """测试获取统计信息"""
        stats = rule_engine.get_statistics()
        
        assert stats["total_rules"] == 1
        assert stats["enabled_rules"] == 1
        assert stats["is_running"] is False


class TestRuleEngineIntegration:
    """规则引擎集成测试"""

    def test_complex_scenario(self):
        """测试复杂场景"""
        parser = RuleParser()
        
        # 复杂规则：污水处理厂综合异常
        rule = {
            "type": "logic",
            "operator": "OR",
            "conditions": [
                {
                    "type": "logic",
                    "operator": "AND",
                    "conditions": [
                        {"type": "threshold", "metric": "DO", "operator": "<", "threshold": 2.0},
                        {"type": "threshold", "metric": "PH", "operator": "<", "threshold": 6.0}
                    ]
                },
                {
                    "type": "threshold",
                    "metric": "COD",
                    "operator": ">",
                    "threshold": 100
                }
            ]
        }
        
        func = parser.compile_condition(rule)
        
        # 场景1：低DO且低pH
        assert func({"DO": 1.5, "PH": 5.5, "COD": 50}) is True
        
        # 场景2：COD超标
        assert func({"DO": 3.0, "PH": 7.0, "COD": 150}) is True
        
        # 场景3：全部正常
        assert func({"DO": 3.0, "PH": 7.0, "COD": 50}) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
