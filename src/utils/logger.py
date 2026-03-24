"""
日志配置工具
"""

import sys
from loguru import logger
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    console_output: bool = True,
    file_output: bool = True
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_dir: 日志文件目录
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
    """
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出
    if console_output:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan> | {message}",
            level=log_level,
            colorize=True
        )
    
    # 文件输出
    if file_output:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 应用日志
        logger.add(
            log_path / "app.log",
            rotation="10 MB",
            retention="30 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}"
        )
        
        # 错误日志
        logger.add(
            log_path / "error.log",
            rotation="10 MB",
            retention="30 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}"
        )
    
    logger.info(f"日志系统初始化完成 (级别：{log_level})")


# 使用示例
if __name__ == "__main__":
    setup_logging(log_level="DEBUG")
    
    logger.debug("这是一条调试信息")
    logger.info("这是一条信息")
    logger.warning("这是一条警告")
    logger.error("这是一条错误")
