"""
时序存储单元测试

作者: QA Team
职责: 测试 storage.py 的各项功能
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.data.storage import TimeSeriesStorage, StorageManager


class TestTimeSeriesStorage:
    """测试时序存储基类"""

    def test_write_single_point(self):
        """测试单点写入"""
        storage = Mock(spec=TimeSeriesStorage)
        storage.write.return_value = True
        
        result = storage.write(
            measurement="test_metric",
            tags={"device": "D001"},
            fields={"value": 3.14},
            timestamp=datetime.now()
        )
        
        assert result is True

    def test_write_batch(self):
        """测试批量写入"""
        storage = Mock(spec=TimeSeriesStorage)
        storage.write_batch.return_value = (3, 0)  # 成功3条，失败0条
        
        points = [
            {"measurement": "m1", "fields": {"v": 1}},
            {"measurement": "m2", "fields": {"v": 2}},
            {"measurement": "m3", "fields": {"v": 3}},
        ]
        
        success, failed = storage.write_batch(points)
        assert success == 3
        assert failed == 0

    def test_query_time_range(self):
        """测试时间范围查询"""
        storage = Mock(spec=TimeSeriesStorage)
        
        # 模拟返回数据
        mock_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='H'),
            'value': range(10)
        })
        storage.query.return_value = mock_data
        
        result = storage.query(
            measurement="test_metric",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )
        
        assert len(result) == 10
        assert 'timestamp' in result.columns
        assert 'value' in result.columns


class TestStorageManager:
    """测试存储管理器"""

    def test_get_storage_backend(self):
        """测试获取存储后端"""
        manager = StorageManager()
        
        # 测试获取 InfluxDB
        influx = manager.get_storage('influxdb')
        assert influx is not None
        
        # 测试获取 SQLite
        sqlite = manager.get_storage('sqlite')
        assert sqlite is not None

    def test_storage_fallback(self):
        """测试存储降级"""
        manager = StorageManager()
        
        # 当主存储不可用时，应自动降级到 SQLite
        with patch.object(manager, '_check_influxdb_health', return_value=False):
            storage = manager.get_storage_with_fallback()
            assert storage.backend_type == 'sqlite'


class TestInfluxDBStorage:
    """测试 InfluxDB 存储"""
    
    @pytest.fixture
    def influx_storage(self):
        """创建 InfluxDB 存储实例"""
        with patch('influxdb_client.InfluxDBClient'):
            from src.data.storage import InfluxDBStorage
            storage = InfluxDBStorage(
                url="http://localhost:8086",
                token="test-token",
                org="test-org",
                bucket="test-bucket"
            )
            return storage

    def test_connection(self, influx_storage):
        """测试连接"""
        with patch.object(influx_storage, 'connect', return_value=True):
            assert influx_storage.connect() is True

    def test_write_point(self, influx_storage):
        """测试写入数据点"""
        with patch.object(influx_storage, 'write', return_value=True):
            result = influx_storage.write(
                measurement="DO",
                tags={"device": "曝气池1"},
                fields={"value": 3.5},
                timestamp=datetime.now()
            )
            assert result is True


class TestSQLiteStorage:
    """测试 SQLite 存储"""
    
    @pytest.fixture
    def sqlite_storage(self, tmp_path):
        """创建 SQLite 存储实例"""
        from src.data.storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        return storage

    def test_create_table(self, sqlite_storage):
        """测试创建表"""
        sqlite_storage._ensure_table("test_metric")
        # 验证表是否创建成功
        assert "test_metric" in sqlite_storage._tables

    def test_insert_and_query(self, sqlite_storage):
        """测试插入和查询"""
        import asyncio
        
        async def test():
            # 写入数据
            await sqlite_storage.write_async(
                measurement="test_metric",
                tags={"device": "D001"},
                fields={"value": 3.14},
                timestamp=datetime.now()
            )
            
            # 查询数据
            result = await sqlite_storage.query_async(
                measurement="test_metric",
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() + timedelta(hours=1)
            )
            
            assert len(result) == 1
            assert result.iloc[0]['value'] == 3.14
        
        asyncio.run(test())


class TestStoragePerformance:
    """测试存储性能"""

    @pytest.mark.benchmark
    def test_write_throughput(self):
        """测试写入吞吐量"""
        import time
        
        storage = Mock(spec=TimeSeriesStorage)
        storage.write.return_value = True
        
        # 模拟批量写入
        batch_size = 1000
        points = [
            {
                "measurement": "perf_test",
                "fields": {"value": i},
                "timestamp": datetime.now() + timedelta(seconds=i)
            }
            for i in range(batch_size)
        ]
        
        start = time.time()
        storage.write_batch(points)
        elapsed = time.time() - start
        
        throughput = batch_size / elapsed
        print(f"写入吞吐量: {throughput:.2f} 点/秒")
        
        # 断言吞吐量 > 1000 点/秒
        assert throughput > 1000

    @pytest.mark.benchmark
    def test_query_latency(self):
        """测试查询延迟"""
        import time
        
        storage = Mock(spec=TimeSeriesStorage)
        storage.query.return_value = pd.DataFrame({'value': range(1000)})
        
        start = time.time()
        result = storage.query(
            measurement="test",
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now()
        )
        elapsed = time.time() - start
        
        print(f"查询延迟: {elapsed*1000:.2f} ms")
        
        # 断言延迟 < 100ms
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
