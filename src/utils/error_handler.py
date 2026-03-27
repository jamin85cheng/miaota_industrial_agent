"""
全局错误处理模块

后端工程师修复: 统一的异常处理和错误传播机制
"""

import sys
import traceback
from typing import Any, Dict, Callable, Optional, Type
from functools import wraps
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class ErrorCategory(Enum):
    """错误分类"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    INTERNAL = "internal"


@dataclass
class ApplicationError(Exception):
    """应用错误基类"""
    message: str
    category: ErrorCategory = ErrorCategory.INTERNAL
    code: str = "UNKNOWN_ERROR"
    details: Optional[Dict[str, Any]] = None
    status_code: int = 500
    
    def __post_init__(self):
        super().__init__(self.message)


class ValidationError(ApplicationError):
    """验证错误"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field, **kwargs} if field else kwargs
        )


class AuthenticationError(ApplicationError):
    """认证错误"""
    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            details=kwargs
        )


class AuthorizationError(ApplicationError):
    """授权错误"""
    def __init__(self, message: str = "权限不足", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=kwargs
        )


class ResourceNotFoundError(ApplicationError):
    """资源不存在错误"""
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        super().__init__(
            message=f"{resource_type} '{resource_id}' 不存在",
            category=ErrorCategory.NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id, **kwargs}
        )


class DatabaseError(ApplicationError):
    """数据库错误"""
    def __init__(self, message: str = "数据库操作失败", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            code="DATABASE_ERROR",
            status_code=500,
            details=kwargs
        )


class ExternalServiceError(ApplicationError):
    """外部服务错误"""
    def __init__(self, service_name: str, message: str = "外部服务调用失败", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details={"service_name": service_name, **kwargs}
        )


class CircuitBreakerOpenError(ApplicationError):
    """熔断器打开错误"""
    def __init__(self, service_name: str, **kwargs):
        super().__init__(
            message=f"服务 {service_name} 暂时不可用（熔断器打开）",
            category=ErrorCategory.EXTERNAL_SERVICE,
            code="CIRCUIT_BREAKER_OPEN",
            status_code=503,
            details={"service_name": service_name, **kwargs}
        )


class ErrorHandler:
    """
    错误处理器
    
    提供统一的错误处理机制
    """
    
    _handlers: Dict[Type[Exception], Callable] = {}
    _fallback_handler: Optional[Callable] = None
    
    @classmethod
    def register(cls, exception_type: Type[Exception], handler: Callable):
        """注册错误处理器"""
        cls._handlers[exception_type] = handler
    
    @classmethod
    def set_fallback(cls, handler: Callable):
        """设置兜底处理器"""
        cls._fallback_handler = handler
    
    @classmethod
    def handle(cls, exception: Exception) -> Dict[str, Any]:
        """
        处理异常
        
        Args:
            exception: 异常对象
            
        Returns:
            错误响应字典
        """
        # 查找专用处理器
        for exc_type, handler in cls._handlers.items():
            if isinstance(exception, exc_type):
                return handler(exception)
        
        # 处理ApplicationError
        if isinstance(exception, ApplicationError):
            return cls._handle_application_error(exception)
        
        # 使用兜底处理器
        if cls._fallback_handler:
            return cls._fallback_handler(exception)
        
        # 默认处理
        return cls._handle_unknown_error(exception)
    
    @staticmethod
    def _handle_application_error(error: ApplicationError) -> Dict[str, Any]:
        """处理应用错误"""
        # 记录日志
        logger.error(
            f"应用错误: {error.message}",
            category=error.category.value,
            code=error.code,
            details=error.details
        )
        
        return {
            "error": {
                "code": error.code,
                "message": error.message,
                "category": error.category.value,
                "details": error.details
            }
        }
    
    @staticmethod
    def _handle_unknown_error(error: Exception) -> Dict[str, Any]:
        """处理未知错误"""
        # 记录详细错误信息
        logger.exception(f"未处理的异常: {error}")
        
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "category": ErrorCategory.INTERNAL.value
            }
        }


def with_error_handling(error_category: ErrorCategory = ErrorCategory.INTERNAL,
                        log_level: str = "error"):
    """
    错误处理装饰器
    
    Args:
        error_category: 错误分类
        log_level: 日志级别
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ApplicationError:
                # 已经是应用错误，直接抛出
                raise
            except Exception as e:
                # 包装为应用错误
                log_func = getattr(logger, log_level)
                log_func(f"函数 {func.__name__} 执行失败: {e}")
                
                raise ApplicationError(
                    message=str(e),
                    category=error_category,
                    code=f"{error_category.value.upper()}_ERROR"
                ) from e
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ApplicationError:
                raise
            except Exception as e:
                log_func = getattr(logger, log_level)
                log_func(f"函数 {func.__name__} 执行失败: {e}")
                
                raise ApplicationError(
                    message=str(e),
                    category=error_category,
                    code=f"{error_category.value.upper()}_ERROR"
                ) from e
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def safe_execute(func: Callable, default: Any = None, log_errors: bool = True):
    """
    安全执行函数
    
    Args:
        func: 要执行的函数
        default: 失败时的默认值
        log_errors: 是否记录错误
        
    Returns:
        函数返回值或默认值
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"安全执行失败: {e}")
        return default


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    logger.warning(
                        f"尝试 {attempt + 1}/{max_attempts} 失败: {e}，"
                        f"{current_delay}s 后重试..."
                    )
                    
                    import time
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    
    return decorator


# 全局异常处理器（用于捕获未处理的异常）
def setup_global_exception_handler():
    """设置全局异常处理器"""
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        """处理未捕获的异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 保留键盘中断的默认处理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # 记录详细错误
        logger.critical(
            "未捕获的异常",
            exception_type=exc_type.__name__,
            exception_message=str(exc_value),
            traceback="".join(traceback.format_tb(exc_traceback))
        )
    
    sys.excepthook = handle_exception
    
    # 处理线程中的未捕获异常
    import threading
    
    def handle_thread_exception(args):
        """处理线程中的未捕获异常"""
        logger.critical(
            f"线程 {args.thread.name} 中未捕获的异常",
            exception_type=args.exc_type.__name__,
            exception_message=str(args.exc_value),
            traceback="".join(traceback.format_tb(args.exc_traceback))
        )
    
    threading.excepthook = handle_thread_exception


# 使用示例
if __name__ == "__main__":
    # 设置全局异常处理
    setup_global_exception_handler()
    
    # 测试自定义错误
    try:
        raise ValidationError("字段不能为空", field="username")
    except ApplicationError as e:
        response = ErrorHandler.handle(e)
        print(f"错误响应: {response}")
    
    # 测试重试装饰器
    @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
    def flaky_operation():
        import random
        if random.random() < 0.7:
            raise ValueError("随机失败")
        return "成功"
    
    try:
        result = flaky_operation()
        print(f"重试结果: {result}")
    except Exception as e:
        print(f"最终失败: {e}")
    
    # 测试安全执行
    result = safe_execute(lambda: 1/0, default=0)
    print(f"安全执行结果: {result}")
