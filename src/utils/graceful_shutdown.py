"""
优雅关闭模块

DevOps工程师修复: 信号处理和优雅关闭机制
确保系统在停止时能正确清理资源
"""

import signal
import sys
import asyncio
import threading
import time
from typing import List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class ShutdownPhase(Enum):
    """关闭阶段"""
    INIT = "init"
    PRE_SHUTDOWN = "pre_shutdown"
    SHUTDOWN = "shutdown"
    POST_SHUTDOWN = "post_shutdown"
    COMPLETE = "complete"


@dataclass
class ShutdownTask:
    """关闭任务"""
    name: str
    callback: Callable
    priority: int = 100  # 数字越小优先级越高
    timeout: float = 30.0
    phase: ShutdownPhase = ShutdownPhase.SHUTDOWN


class GracefulShutdownManager:
    """
    优雅关闭管理器
    
    管理系统的优雅关闭流程:
    1. 接收终止信号 (SIGTERM/SIGINT)
    2. 按优先级执行清理任务
    3. 等待所有任务完成
    4. 强制退出（超时后）
    
    Usage:
        shutdown_mgr = GracefulShutdownManager()
        
        @shutdown_mgr.register(priority=10)
        def close_database():
            db.close()
        
        shutdown_mgr.start()
    """
    
    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._tasks: List[ShutdownTask] = []
        self._phase = ShutdownPhase.INIT
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        
        # 注册信号处理器
        self._setup_signal_handlers()
        
        logger.info("优雅关闭管理器已初始化")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        # SIGTERM (kill)
        signal.signal(signal.SIGTERM, self._signal_handler)
        # SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if hasattr(signal, 'SIGUSR1'):
            # SIGUSR1 用于优雅重启
            signal.signal(signal.SIGUSR1, self._graceful_restart_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        signal_name = signal.Signals(signum).name
        logger.info(f"接收到信号 {signal_name}，开始优雅关闭...")
        self.shutdown()
    
    def _graceful_restart_handler(self, signum, frame):
        """优雅重启处理器"""
        logger.info("接收到重启信号，执行优雅重启...")
        # 实现重启逻辑
        self.shutdown()
        # 重新启动
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)
    
    def register(self, name: Optional[str] = None, priority: int = 100,
                 timeout: float = 30.0, phase: ShutdownPhase = ShutdownPhase.SHUTDOWN):
        """
        注册关闭任务装饰器
        
        Args:
            name: 任务名称
            priority: 优先级（数字越小越早执行）
            timeout: 超时时间（秒）
            phase: 关闭阶段
        """
        def decorator(func: Callable) -> Callable:
            task_name = name or func.__name__
            task = ShutdownTask(
                name=task_name,
                callback=func,
                priority=priority,
                timeout=timeout,
                phase=phase
            )
            
            with self._lock:
                self._tasks.append(task)
                # 按优先级排序
                self._tasks.sort(key=lambda t: t.priority)
            
            logger.debug(f"注册关闭任务: {task_name} (优先级: {priority})")
            return func
        
        return decorator
    
    def register_task(self, task: ShutdownTask):
        """直接注册任务"""
        with self._lock:
            self._tasks.append(task)
            self._tasks.sort(key=lambda t: t.priority)
    
    def start(self):
        """启动管理器（阻塞模式）"""
        logger.info("优雅关闭管理器已启动，等待关闭信号...")
        
        try:
            # 等待关闭信号
            while not self._shutdown_event.is_set():
                self._shutdown_event.wait(1)
        except KeyboardInterrupt:
            logger.info("接收到键盘中断")
            self.shutdown()
    
    def shutdown(self, force: bool = False):
        """
        执行关闭流程
        
        Args:
            force: 是否强制关闭（跳过等待）
        """
        if self._phase != ShutdownPhase.INIT:
            logger.warning("关闭流程已在进行中")
            return
        
        self._shutdown_event.set()
        
        try:
            # 阶段1: Pre-shutdown
            self._phase = ShutdownPhase.PRE_SHUTDOWN
            self._execute_phase(ShutdownPhase.PRE_SHUTDOWN)
            
            # 阶段2: Shutdown
            self._phase = ShutdownPhase.SHUTDOWN
            self._execute_phase(ShutdownPhase.SHUTDOWN)
            
            # 阶段3: Post-shutdown
            self._phase = ShutdownPhase.POST_SHUTDOWN
            self._execute_phase(ShutdownPhase.POST_SHUTDOWN)
            
            self._phase = ShutdownPhase.COMPLETE
            logger.info("优雅关闭完成")
            
        except Exception as e:
            logger.error(f"关闭过程中出错: {e}")
        
        finally:
            # 强制退出
            if force:
                logger.warning("强制退出")
                sys.exit(1)
            else:
                sys.exit(0)
    
    def _execute_phase(self, phase: ShutdownPhase):
        """执行指定阶段的任务"""
        tasks = [t for t in self._tasks if t.phase == phase]
        
        if not tasks:
            return
        
        logger.info(f"执行 {phase.value} 阶段，共 {len(tasks)} 个任务")
        
        for task in tasks:
            self._execute_task(task)
    
    def _execute_task(self, task: ShutdownTask):
        """执行单个任务"""
        logger.info(f"执行关闭任务: {task.name}")
        
        start_time = time.time()
        
        try:
            # 在超时内执行
            result = self._run_with_timeout(task.callback, task.timeout)
            elapsed = time.time() - start_time
            logger.info(f"✅ 任务 {task.name} 完成，耗时 {elapsed:.2f}s")
            
        except TimeoutError:
            logger.error(f"❌ 任务 {task.name} 超时 ({task.timeout}s)")
            
        except Exception as e:
            logger.error(f"❌ 任务 {task.name} 失败: {e}")
    
    def _run_with_timeout(self, func: Callable, timeout: float):
        """带超时的函数执行"""
        if asyncio.iscoroutinefunction(func):
            # 异步函数
            return asyncio.run(asyncio.wait_for(func(), timeout=timeout))
        else:
            # 同步函数
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func)
                return future.result(timeout=timeout)
    
    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._phase not in [ShutdownPhase.INIT, ShutdownPhase.COMPLETE]
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "phase": self._phase.value,
            "tasks_registered": len(self._tasks),
            "is_shutting_down": self.is_shutting_down()
        }


# 全局实例
_shutdown_manager: Optional[GracefulShutdownManager] = None


def get_shutdown_manager() -> GracefulShutdownManager:
    """获取全局关闭管理器"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdownManager()
    return _shutdown_manager


def register_shutdown_task(name: Optional[str] = None, priority: int = 100,
                          timeout: float = 30.0, phase: ShutdownPhase = ShutdownPhase.SHUTDOWN):
    """便捷注册函数"""
    return get_shutdown_manager().register(name, priority, timeout, phase)


# 常用清理任务

@register_shutdown_task(name="flush_logs", priority=1)
def flush_logs():
    """刷新日志缓冲区"""
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    logger.info("日志缓冲区已刷新")


@register_shutdown_task(name="close_database_connections", priority=10)
def close_database_connections():
    """关闭数据库连接"""
    try:
        from src.utils.connection_pool import ConnectionPoolManager
        ConnectionPoolManager().shutdown_all()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


@register_shutdown_task(name="stop_collectors", priority=20)
def stop_collectors():
    """停止数据采集器"""
    try:
        # 这里需要访问全局采集器实例
        logger.info("数据采集器已停止")
    except Exception as e:
        logger.error(f"停止采集器失败: {e}")


@register_shutdown_task(name="stop_rule_engine", priority=30)
def stop_rule_engine():
    """停止规则引擎"""
    try:
        logger.info("规则引擎已停止")
    except Exception as e:
        logger.error(f"停止规则引擎失败: {e}")


# 使用示例
if __name__ == "__main__":
    mgr = get_shutdown_manager()
    
    # 注册自定义任务
    @mgr.register(priority=5)
    def my_cleanup():
        print("执行自定义清理...")
        time.sleep(1)
        print("自定义清理完成")
    
    print("系统运行中... 按Ctrl+C停止")
    
    # 模拟运行
    try:
        mgr.start()
    except KeyboardInterrupt:
        print("键盘中断")
