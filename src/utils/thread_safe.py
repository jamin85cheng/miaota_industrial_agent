"""
并发安全模块

后端工程师修复: 线程安全的资源管理、锁优化
"""

import threading
import asyncio
from typing import Any, Dict, Optional, TypeVar, Generic, Callable
from dataclasses import dataclass
from contextlib import contextmanager
from loguru import logger


T = TypeVar('T')


@dataclass
class SafeValue(Generic[T]):
    """线程安全的值容器"""
    _value: T
    _lock: threading.RLock = threading.RLock()
    
    def get(self) -> T:
        """获取值"""
        with self._lock:
            return self._value
    
    def set(self, value: T):
        """设置值"""
        with self._lock:
            self._value = value
    
    def update(self, func: Callable[[T], T]) -> T:
        """原子更新"""
        with self._lock:
            self._value = func(self._value)
            return self._value


class ThreadSafeDict(Generic[T]):
    """线程安全的字典"""
    
    def __init__(self):
        self._data: Dict[str, T] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        with self._lock:
            return self._data.get(key, default)
    
    def set(self, key: str, value: T):
        with self._lock:
            self._data[key] = value
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._data
    
    def keys(self) -> list:
        with self._lock:
            return list(self._data.keys())
    
    def values(self) -> list:
        with self._lock:
            return list(self._data.values())
    
    def items(self) -> list:
        with self._lock:
            return list(self._data.items())
    
    def size(self) -> int:
        with self._lock:
            return len(self._data)
    
    def clear(self):
        with self._lock:
            self._data.clear()
    
    @contextmanager
    def get_or_create(self, key: str, factory: Callable[[], T]):
        """获取或创建，返回上下文管理器"""
        with self._lock:
            if key not in self._data:
                self._data[key] = factory()
            yield self._data[key]


class ReadWriteLock:
    """
    读写锁
    
    允许多个读操作并行，写操作互斥
    """
    
    def __init__(self):
        self._readers = 0
        self._writers = 0
        self._read_ready = threading.Condition(threading.RLock())
    
    @contextmanager
    def read_lock(self):
        """获取读锁"""
        with self._read_ready:
            while self._writers > 0:
                self._read_ready.wait()
            self._readers += 1
        
        try:
            yield
        finally:
            with self._read_ready:
                self._readers -= 1
                if self._readers == 0:
                    self._read_ready.notify_all()
    
    @contextmanager
    def write_lock(self):
        """获取写锁"""
        with self._read_ready:
            while self._readers > 0 or self._writers > 0:
                self._read_ready.wait()
            self._writers += 1
        
        try:
            yield
        finally:
            with self._read_ready:
                self._writers -= 1
                self._read_ready.notify_all()


class AsyncSafeDict(Generic[T]):
    """异步安全的字典"""
    
    def __init__(self):
        self._data: Dict[str, T] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        async with self._lock:
            return self._data.get(key, default)
    
    async def set(self, key: str, value: T):
        async with self._lock:
            self._data[key] = value
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    async def contains(self, key: str) -> bool:
        async with self._lock:
            return key in self._data


class ConnectionGuard:
    """
    连接守护器
    
    管理资源连接状态，确保线程安全
    """
    
    def __init__(self, name: str):
        self.name = name
        self._is_connected = False
        self._client = None
        self._lock = threading.RLock()
        self._connect_lock = threading.Lock()  # 连接锁，防止并发连接
    
    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._is_connected
    
    @property
    def client(self):
        with self._lock:
            return self._client
    
    def connect(self, factory: Callable) -> bool:
        """
        连接（线程安全）
        
        Args:
            factory: 连接工厂函数
            
        Returns:
            是否成功
        """
        # 使用连接锁防止并发连接
        with self._connect_lock:
            with self._lock:
                if self._is_connected:
                    return True
                
                try:
                    self._client = factory()
                    self._is_connected = True
                    logger.info(f"{self.name} 连接成功")
                    return True
                except Exception as e:
                    logger.error(f"{self.name} 连接失败: {e}")
                    self._client = None
                    self._is_connected = False
                    return False
    
    def disconnect(self, cleanup: Optional[Callable] = None):
        """断开连接"""
        with self._lock:
            if not self._is_connected:
                return
            
            try:
                if cleanup and self._client:
                    cleanup(self._client)
                self._client = None
                self._is_connected = False
                logger.info(f"{self.name} 已断开")
            except Exception as e:
                logger.error(f"{self.name} 断开连接失败: {e}")
    
    @contextmanager
    def use(self):
        """使用连接上下文管理器"""
        with self._lock:
            if not self._is_connected:
                raise Exception(f"{self.name} 未连接")
            yield self._client


class RateLimitedExecutor:
    """速率限制的执行器"""
    
    def __init__(self, max_rate: int, period: float = 1.0):
        self.max_rate = max_rate
        self.period = period
        self._tokens = max_rate
        self._last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """获取令牌"""
        with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            
            # 补充令牌
            self._tokens = min(
                self.max_rate,
                self._tokens + elapsed * (self.max_rate / self.period)
            )
            self._last_update = now
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
    
    def execute(self, func: Callable, tokens: int = 1, timeout: float = 10.0):
        """执行函数（带速率限制）"""
        import time as time_module
        
        start = time_module.time()
        while not self.acquire(tokens):
            if time_module.time() - start > timeout:
                raise TimeoutError("速率限制超时")
            time_module.sleep(0.1)
        
        return func()


import time


class CircuitBreaker:
    """
    熔断器
    
    防止级联故障，在服务不可用时快速失败
    """
    
    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()
    
    def is_closed(self) -> bool:
        """检查熔断器是否关闭"""
        with self._lock:
            if self._state == "closed":
                return True
            
            if self._state == "open":
                # 检查是否应该进入半开状态
                if (self._last_failure_time and
                    time.time() - self._last_failure_time > self.recovery_timeout):
                    self._state = "half-open"
                    return True
                return False
            
            return True  # half-open
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self._failures = 0
            self._state = "closed"
    
    def record_failure(self):
        """记录失败"""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            
            if self._failures >= self.failure_threshold:
                self._state = "open"
                logger.warning(f"熔断器 {self.name} 已打开")
    
    @contextmanager
    def guard(self):
        """熔断保护上下文管理器"""
        if not self.is_closed():
            raise Exception(f"熔断器 {self.name} 已打开，拒绝请求")
        
        try:
            yield
            self.record_success()
        except Exception as e:
            self.record_failure()
            raise


# 使用示例
if __name__ == "__main__":
    # 线程安全字典测试
    safe_dict = ThreadSafeDict[int]()
    safe_dict.set("key1", 100)
    print(f"key1 = {safe_dict.get('key1')}")
    
    # 读写锁测试
    rw_lock = ReadWriteLock()
    
    # 读操作
    with rw_lock.read_lock():
        print("读取数据...")
    
    # 写操作
    with rw_lock.write_lock():
        print("写入数据...")
    
    # 连接守护器测试
    guard = ConnectionGuard("test_conn")
    guard.connect(lambda: "connected_client")
    print(f"连接状态: {guard.is_connected}")
    
    # 熔断器测试
    breaker = CircuitBreaker("test_breaker", failure_threshold=2)
    
    for i in range(5):
        try:
            with breaker.guard():
                if i < 2:
                    raise Exception("模拟失败")
                print(f"请求 {i} 成功")
        except Exception as e:
            print(f"请求 {i} 失败: {e}")
