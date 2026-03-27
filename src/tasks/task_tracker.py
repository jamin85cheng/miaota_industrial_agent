"""
长时任务追踪系统

支持异步任务管理和进度追踪
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import json
import uuid

from src.utils.structured_logging import get_logger
from src.utils.thread_safe import ThreadSafeDict

logger = get_logger("task_tracker")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class TaskProgress:
    """任务进度"""
    current_step: int = 0
    total_steps: int = 100
    current_action: str = ""
    percentage: float = 0.0
    estimated_remaining_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_action": self.current_action,
            "percentage": round(self.percentage, 1),
            "estimated_remaining_seconds": self.estimated_remaining_seconds
        }
    
    def update(self, step: int = None, action: str = None, total: int = None):
        """更新进度"""
        if step is not None:
            self.current_step = step
        if action:
            self.current_action = action
        if total:
            self.total_steps = total
        
        if self.total_steps > 0:
            self.percentage = (self.current_step / self.total_steps) * 100


@dataclass
class TrackedTask:
    """被追踪的任务"""
    task_id: str
    task_type: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    
    # 时间戳
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 执行信息
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Any = None
    error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    sub_task_ids: List[str] = field(default_factory=list)
    
    # 回调
    on_progress: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress.to_dict(),
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "parent_task_id": self.parent_task_id,
            "sub_task_ids": self.sub_task_ids
        }
    
    def duration_seconds(self) -> Optional[float]:
        """计算任务持续时间"""
        if self.started_at:
            end = self.completed_at or datetime.utcnow()
            return (end - self.started_at).total_seconds()
        return None
    
    def is_active(self) -> bool:
        """检查任务是否活跃"""
        return self.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED]


class TaskTracker:
    """
    任务追踪器
    
    管理长时间运行的异步任务
    """
    
    def __init__(self, max_concurrent: int = 10, default_timeout: int = 3600):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        
        # 任务存储
        self._tasks: ThreadSafeDict = ThreadSafeDict()
        
        # 执行控制
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 事件监听
        self._listeners: Dict[str, List[Callable]] = {
            "progress": [],
            "complete": [],
            "fail": []
        }
        
        # 统计
        self._stats = {
            "total_created": 0,
            "total_completed": 0,
            "total_failed": 0
        }
        
        logger.info(f"任务追踪器初始化: 最大并发={max_concurrent}")
    
    def create_task(self, task_type: str, description: str,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   metadata: Dict[str, Any] = None,
                   parent_task_id: Optional[str] = None) -> TrackedTask:
        """
        创建任务
        
        Args:
            task_type: 任务类型
            description: 任务描述
            priority: 优先级
            metadata: 元数据
            parent_task_id: 父任务ID
        
        Returns:
            任务对象
        """
        task_id = f"TASK_{uuid.uuid4().hex[:12].upper()}"
        
        task = TrackedTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
            parent_task_id=parent_task_id
        )
        
        self._tasks.set(task_id, task)
        self._stats["total_created"] += 1
        
        logger.info(f"任务创建: {task_id} - {description}")
        
        return task
    
    async def execute(self, task: TrackedTask, 
                     coro_func: Callable, *args, **kwargs) -> Any:
        """
        执行任务
        
        Args:
            task: 任务对象
            coro_func: 异步函数
            *args, **kwargs: 函数参数
        
        Returns:
            执行结果
        """
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            logger.info(f"任务开始执行: {task.task_id}")
            
            try:
                # 创建异步任务
                async_task = asyncio.create_task(
                    self._run_with_timeout(task, coro_func, *args, **kwargs)
                )
                
                self._running_tasks[task.task_id] = async_task
                
                # 等待完成
                result = await async_task
                
                # 标记完成
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.utcnow()
                
                self._stats["total_completed"] += 1
                
                # 触发回调
                if task.on_complete:
                    await task.on_complete(task)
                
                self._trigger_event("complete", task)
                
                logger.info(f"任务完成: {task.task_id}")
                
                return result
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = "任务执行超时"
                task.completed_at = datetime.utcnow()
                
                self._stats["total_failed"] += 1
                self._trigger_event("fail", task)
                
                logger.warning(f"任务超时: {task.task_id}")
                raise
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.utcnow()
                
                self._stats["total_failed"] += 1
                
                self._trigger_event("fail", task)
                
                logger.error(f"任务失败: {task.task_id} - {e}")
                raise
                
            finally:
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]
    
    async def _run_with_timeout(self, task: TrackedTask, 
                               coro_func: Callable, *args, **kwargs):
        """带超时的执行"""
        timeout = task.metadata.get("timeout_seconds", self.default_timeout)
        
        return await asyncio.wait_for(
            coro_func(task, *args, **kwargs),
            timeout=timeout
        )
    
    def update_progress(self, task_id: str, step: int = None, 
                       action: str = None, percentage: float = None):
        """更新任务进度"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        if step is not None:
            task.progress.current_step = step
        if action:
            task.progress.current_action = action
        if percentage is not None:
            task.progress.percentage = percentage
        
        # 触发回调
        if task.on_progress:
            asyncio.create_task(task.on_progress(task))
        
        self._trigger_event("progress", task)
    
    def get_task(self, task_id: str) -> Optional[TrackedTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        if task:
            return {
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress.to_dict(),
                "duration_seconds": task.duration_seconds()
            }
        return None
    
    def list_tasks(self, status: TaskStatus = None, 
                  task_type: str = None, limit: int = 100) -> List[TrackedTask]:
        """列出任务"""
        tasks = []
        
        for task_id in self._tasks.keys():
            task = self._tasks.get(task_id)
            if not task:
                continue
            
            # 状态过滤
            if status and task.status != status:
                continue
            
            # 类型过滤
            if task_type and task.task_type != task_type:
                continue
            
            tasks.append(task)
        
        # 按优先级和时间排序
        tasks.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
        
        return tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.task_id in self._running_tasks:
            async_task = self._running_tasks[task_id]
            async_task.cancel()
            
            try:
                await async_task
            except asyncio.CancelledError:
                pass
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        
        logger.info(f"任务已取消: {task_id}")
        return True
    
    def add_listener(self, event_type: str, callback: Callable):
        """添加事件监听器"""
        if event_type in self._listeners:
            self._listeners[event_type].append(callback)
    
    def _trigger_event(self, event_type: str, task: TrackedTask):
        """触发事件"""
        for callback in self._listeners.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(task))
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"事件处理失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        active_count = sum(1 for tid in self._tasks.keys() 
                         if self._tasks.get(tid).is_active())
        
        return {
            "total_created": self._stats["total_created"],
            "total_completed": self._stats["total_completed"],
            "total_failed": self._stats["total_failed"],
            "active_tasks": active_count,
            "running_tasks": len(self._running_tasks),
            "success_rate": (
                self._stats["total_completed"] / 
                (self._stats["total_completed"] + self._stats["total_failed"])
                if (self._stats["total_completed"] + self._stats["total_failed"]) > 0 
                else 0
            )
        }
    
    def create_subtask(self, parent_task_id: str, description: str,
                      task_type: str = "subtask") -> Optional[TrackedTask]:
        """创建子任务"""
        parent = self._tasks.get(parent_task_id)
        if not parent:
            return None
        
        subtask = self.create_task(
            task_type=task_type,
            description=description,
            priority=parent.priority,
            parent_task_id=parent_task_id
        )
        
        parent.sub_task_ids.append(subtask.task_id)
        
        return subtask
    
    async def execute_with_progress(self, task: TrackedTask,
                                   steps: List[Dict[str, Any]],
                                   step_func: Callable) -> Any:
        """
        分步骤执行任务，自动更新进度
        
        Args:
            task: 任务对象
            steps: 步骤定义列表 [{"name": "", "weight": 1}]
            step_func: 步骤执行函数 async def step_func(task, step_info)
        
        Returns:
            最终结果
        """
        task.progress.total_steps = len(steps)
        results = []
        
        for i, step in enumerate(steps):
            # 更新进度
            self.update_progress(
                task.task_id,
                step=i + 1,
                action=step.get("name", f"Step {i+1}"),
                percentage=(i / len(steps)) * 100
            )
            
            # 执行步骤
            try:
                result = await step_func(task, step)
                results.append(result)
            except Exception as e:
                logger.error(f"步骤 {i+1} 失败: {e}")
                raise
        
        # 最终进度
        self.update_progress(task.task_id, step=len(steps), percentage=100)
        
        return results


# 全局任务追踪器实例
task_tracker = TaskTracker()


# 使用示例
async def demo_task_tracker():
    """演示任务追踪"""
    
    async def sample_task(task: TrackedTask, duration: int):
        """示例任务"""
        for i in range(duration):
            task_tracker.update_progress(
                task.task_id,
                step=i + 1,
                action=f"处理中... {i+1}/{duration}",
                percentage=((i + 1) / duration) * 100
            )
            await asyncio.sleep(0.1)
        
        return {"status": "completed", "processed": duration}
    
    # 创建任务
    task = task_tracker.create_task(
        task_type="data_processing",
        description="处理历史数据",
        priority=TaskPriority.HIGH,
        metadata={"timeout_seconds": 60}
    )
    
    # 执行任务
    try:
        result = await task_tracker.execute(task, sample_task, 10)
        print(f"任务结果: {result}")
    except Exception as e:
        print(f"任务失败: {e}")
    
    # 打印统计
    print(json.dumps(task_tracker.get_stats(), indent=2))


if __name__ == "__main__":
    asyncio.run(demo_task_tracker())
