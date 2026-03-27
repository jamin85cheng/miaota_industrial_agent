"""
健康检查API路由

实现OpenAPI中定义的健康检查端点
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any
import time

from src.utils.health_check import HealthChecker, HealthStatus

router = APIRouter(prefix="/health", tags=["健康检查"])

# 健康检查器实例
health_checker = HealthChecker()


@router.get("", response_model=Dict[str, Any])
async def health_check():
    """
    系统健康检查
    
    返回系统整体健康状态，包括各组件检查结果
    """
    start_time = time.time()
    
    # 执行所有检查
    results = await health_checker.check_all()
    
    # 确定整体状态
    overall_status = HealthStatus.HEALTHY
    for result in results.values():
        if result.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
            break
        elif result.status == HealthStatus.DEGRADED:
            overall_status = HealthStatus.DEGRADED
    
    response = {
        "status": overall_status.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "v1.0.0-beta1",
        "response_time_ms": round((time.time() - start_time) * 1000, 2),
        "checks": {}
    }
    
    for name, result in results.items():
        check_info = {
            "status": result.status.value,
            "response_time_ms": round(result.response_time * 1000, 2)
        }
        if result.message:
            check_info["message"] = result.message
        if result.details:
            check_info["details"] = result.details
        
        response["checks"][name] = check_info
    
    return response


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes就绪探针
    
    检查服务是否准备好接收流量
    """
    # 检查关键依赖
    results = await health_checker.check_all()
    
    # 只要有任何关键组件不健康，就不就绪
    critical_components = ["database", "influxdb", "redis"]
    for component in critical_components:
        if component in results:
            if results[component].status == HealthStatus.UNHEALTHY:
                return {"status": "not_ready", "reason": f"{component} unhealthy"}
    
    return "OK"


@router.get("/live")
async def liveness_check():
    """
    Kubernetes存活探针
    
    检查服务是否存活
    """
    # 简单的存活检查
    return "OK"


@router.get("/detailed")
async def detailed_health_check():
    """
    详细健康检查
    
    包含更多诊断信息
    """
    start_time = time.time()
    
    results = await health_checker.check_all()
    
    # 收集系统信息
    import psutil
    import os
    
    system_info = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
        "process_count": len(psutil.pids())
    }
    
    response = {
        "status": HealthStatus.HEALTHY.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "response_time_ms": round((time.time() - start_time) * 1000, 2),
        "system": system_info,
        "components": {}
    }
    
    for name, result in results.items():
        response["components"][name] = {
            "status": result.status.value,
            "response_time_ms": round(result.response_time * 1000, 2),
            "message": result.message,
            "details": result.details
        }
    
    return response
