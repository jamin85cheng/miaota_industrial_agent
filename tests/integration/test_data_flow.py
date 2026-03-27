"""
数据流集成测试

验证从数据采集到存储的完整流程
"""

import pytest
import time
import sqlite3
from datetime import datetime
from pathlib import Path

from src.data.collector import PLCCollector
from src.data.buffer import DataBuffer
from src.core.tag_mapping import TagMappingManager


@pytest.mark.integration
class TestDataCollectionFlow:
    """数据采集流程测试"""
    
    def test_mock_plc_to_buffer(self, temp_db_path):
        """测试模拟PLC数据到缓存"""
        # 创建数据缓存
        buffer = DataBuffer(db_path=temp_db_path, max_size=1000)
        
        # 模拟采集数据
        test_data = {
            "timestamp": datetime.utcnow(),
            "values": {
                "temperature": 25.5,
                "pressure": 1.2
            }
        }
        
        # 写入缓存
        success = buffer.write(
            measurement="sensor_data",
            tags={"device": "PLC_001"},
            fields=test_data["values"],
            timestamp=test_data["timestamp"]
        )
        
        assert success == True
        
        # 验证写入
        points = buffer.read_batch(limit=10)
        assert len(points) == 1
        assert points[0].fields["temperature"] == 25.5
    
    def test_buffer_to_storage_retransmit(self, temp_db_path):
        """测试缓存到存储的补传机制"""
        buffer = DataBuffer(db_path=temp_db_path)
        
        # 写入多条数据
        for i in range(5):
            buffer.write(
                measurement="test",
                tags={"index": str(i)},
                fields={"value": float(i)},
                timestamp=datetime.utcnow()
            )
        
        # 读取待补传数据
        pending = buffer.get_pending_records(limit=10)
        assert len(pending) == 5
        
        # 模拟成功补传
        for record in pending:
            buffer.mark_as_sent(record.id)
        
        # 验证已标记
        pending = buffer.get_pending_records(limit=10)
        assert len(pending) == 0
    
    def test_tag_mapping_integration(self):
        """测试点位映射集成"""
        mapping = TagMappingManager()
        
        # 添加映射规则
        mapping.add_mapping("DB1.DBD0", "temperature", "°C")
        mapping.add_mapping("DB1.DBD4", "pressure", "bar")
        
        # 测试转换
        raw_data = {
            "DB1.DBD0": 25.5,
            "DB1.DBD4": 1.2
        }
        
        semantic_data = mapping.convert_to_semantic(raw_data)
        
        assert "temperature" in semantic_data
        assert semantic_data["temperature"]["value"] == 25.5
        assert semantic_data["temperature"]["unit"] == "°C"


@pytest.mark.integration
class TestRuleEngineFlow:
    """规则引擎流程测试"""
    
    def test_data_to_alert_flow(self, temp_db_path):
        """测试数据到告警的完整流程"""
        from src.rules.rule_engine import RuleEngine
        
        # 创建规则引擎
        engine = RuleEngine(
            config_file="tests/fixtures/test_rules.json",
            evaluation_interval=1
        )
        
        # 创建测试规则
        engine.add_rule({
            "rule_id": "TEST_001",
            "name": "测试规则",
            "enabled": True,
            "condition": {
                "type": "threshold",
                "tag": "temperature",
                "operator": ">",
                "value": 50
            },
            "severity": "critical"
        })
        
        # 收集告警
        alerts = []
        engine.add_alert_callback(lambda alert: alerts.append(alert))
        
        # 触发告警的数据
        data = {"temperature": 60, "pressure": 1.0}
        engine.evaluate(data)
        
        # 验证告警触发
        assert len(alerts) == 1
        assert alerts[0]["rule_name"] == "测试规则"
    
    def test_alert_suppression(self, temp_db_path):
        """测试告警抑制"""
        from src.rules.rule_engine import RuleEngine
        
        engine = RuleEngine(
            config_file="tests/fixtures/test_rules.json",
            evaluation_interval=1
        )
        
        engine.add_rule({
            "rule_id": "TEST_SUPPRESS",
            "name": "抑制测试规则",
            "enabled": True,
            "condition": {
                "type": "threshold",
                "tag": "temp",
                "operator": ">",
                "value": 50
            },
            "severity": "warning"
        })
        
        # 设置短抑制窗口以便测试
        engine.suppression_window_minutes = 0.01  # 0.6秒
        
        alerts = []
        engine.add_alert_callback(lambda alert: alerts.append(alert))
        
        # 连续触发多次
        for _ in range(3):
            engine.evaluate({"temp": 60})
        
        # 应该只触发一次
        assert len(alerts) == 1


@pytest.mark.integration
class TestStorageFlow:
    """存储流程测试"""
    
    def test_influxdb_write_batch(self):
        """测试InfluxDB批量写入"""
        from src.data.storage import DataStorageManager
        
        # 使用模拟存储
        storage = DataStorageManager(connection_string="mock://localhost")
        
        # 批量数据
        points = [
            {
                "measurement": "test",
                "tags": {"device": f"PLC_{i}"},
                "fields": {"value": float(i)},
                "timestamp": datetime.utcnow()
            }
            for i in range(100)
        ]
        
        # 批量写入
        success_count = storage.write_batch(points)
        assert success_count == 100
    
    def test_sqlite_cache_persistence(self, temp_db_path):
        """测试SQLite缓存持久化"""
        # 第一次连接写入数据
        conn1 = sqlite3.connect(temp_db_path)
        conn1.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, value REAL)")
        conn1.execute("INSERT INTO test VALUES (1, 100.0)")
        conn1.commit()
        conn1.close()
        
        # 第二次连接读取数据
        conn2 = sqlite3.connect(temp_db_path)
        cursor = conn2.execute("SELECT * FROM test")
        row = cursor.fetchone()
        conn2.close()
        
        assert row == (1, 100.0)
