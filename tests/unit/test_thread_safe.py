"""
并发安全模块单元测试

后端工程师编写 - 验证并发安全性
"""

import pytest
import threading
import time
from src.utils.thread_safe import (
    SafeValue,
    ThreadSafeDict,
    ReadWriteLock,
    ConnectionGuard,
    CircuitBreaker
)


class TestSafeValue:
    """线程安全值测试"""
    
    def test_basic_operations(self):
        """测试基本操作"""
        value = SafeValue(0)
        assert value.get() == 0
        
        value.set(42)
        assert value.get() == 42
    
    def test_concurrent_access(self):
        """测试并发访问"""
        value = SafeValue(0)
        errors = []
        
        def increment():
            try:
                for _ in range(100):
                    current = value.get()
                    value.set(current + 1)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        # 由于竞态条件，结果可能不是1000
        # 但不应该抛出异常
    
    def test_atomic_update(self):
        """测试原子更新"""
        value = SafeValue(0)
        
        def atomic_increment():
            for _ in range(100):
                value.update(lambda x: x + 1)
        
        threads = [threading.Thread(target=atomic_increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 原子更新应该保证结果正确
        assert value.get() == 1000


class TestThreadSafeDict:
    """线程安全字典测试"""
    
    def test_basic_operations(self):
        """测试基本操作"""
        d = ThreadSafeDict()
        
        d.set("key1", "value1")
        assert d.get("key1") == "value1"
        assert d.get("nonexistent") is None
        
        d.delete("key1")
        assert d.get("key1") is None
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        d = ThreadSafeDict()
        errors = []
        
        def writer(thread_id):
            try:
                for i in range(100):
                    d.set(f"key_{thread_id}_{i}", i)
            except Exception as e:
                errors.append(e)
        
        def reader(thread_id):
            try:
                for i in range(100):
                    d.get(f"key_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader, args=(i,)))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
    
    def test_contains(self):
        """测试contains方法"""
        d = ThreadSafeDict()
        d.set("key", "value")
        
        assert d.contains("key") == True
        assert d.contains("nonexistent") == False


class TestReadWriteLock:
    """读写锁测试"""
    
    def test_read_lock_concurrent(self):
        """测试多个读锁可以并发"""
        lock = ReadWriteLock()
        results = []
        
        def reader():
            with lock.read_lock():
                results.append("read")
                time.sleep(0.1)
        
        threads = [threading.Thread(target=reader) for _ in range(5)]
        start = time.time()
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        elapsed = time.time() - start
        # 如果读锁并发有效，应该远小于0.5秒
        assert elapsed < 0.3
        assert len(results) == 5
    
    def test_write_lock_exclusive(self):
        """测试写锁互斥"""
        lock = ReadWriteLock()
        results = []
        
        def writer(thread_id):
            with lock.write_lock():
                results.append(f"write_{thread_id}")
                time.sleep(0.1)
        
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(3)]
        start = time.time()
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        elapsed = time.time() - start
        # 如果写锁互斥有效，应该大于0.3秒
        assert elapsed >= 0.25
        assert len(results) == 3


class TestConnectionGuard:
    """连接守护器测试"""
    
    def test_connection_management(self):
        """测试连接管理"""
        guard = ConnectionGuard("test_conn")
        
        # 初始状态
        assert guard.is_connected == False
        
        # 模拟连接
        def factory():
            return {"connected": True}
        
        assert guard.connect(factory) == True
        assert guard.is_connected == True
        assert guard.client == {"connected": True}
        
        # 断开连接
        guard.disconnect()
        assert guard.is_connected == False
    
    def test_use_context_manager(self):
        """测试使用上下文管理器"""
        guard = ConnectionGuard("test_conn")
        
        def factory():
            return {"data": "test"}
        
        guard.connect(factory)
        
        with guard.use() as client:
            assert client["data"] == "test"
    
    def test_use_without_connection(self):
        """测试未连接时使用"""
        guard = ConnectionGuard("test_conn")
        
        with pytest.raises(Exception):
            with guard.use() as client:
                pass


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_circuit_closed_initially(self):
        """测试熔断器初始状态为关闭"""
        breaker = CircuitBreaker("test", failure_threshold=3)
        assert breaker.is_closed() == True
    
    def test_circuit_opens_after_failures(self):
        """测试多次失败后熔断器打开"""
        breaker = CircuitBreaker("test", failure_threshold=3)
        
        # 记录3次失败
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.is_closed() == False  # 熔断器打开
    
    def test_circuit_closes_after_success(self):
        """测试成功后熔断器关闭"""
        breaker = CircuitBreaker("test", failure_threshold=3)
        
        # 打开熔断器
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.is_closed() == False
        
        # 记录成功
        breaker.record_success()
        assert breaker.is_closed() == True
    
    def test_guard_success(self):
        """测试guard成功执行"""
        breaker = CircuitBreaker("test")
        
        with breaker.guard():
            result = "success"
        
        assert breaker.is_closed() == True
    
    def test_guard_failure(self):
        """测试guard执行失败"""
        breaker = CircuitBreaker("test", failure_threshold=1)
        
        with pytest.raises(Exception):
            with breaker.guard():
                raise Exception("失败")
        
        # 熔断器状态取决于是否达到阈值
