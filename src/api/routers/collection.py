"""
数据采集API路由

实现数据查询、采集控制等接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from src.api.dependencies import (
    get_current_user, require_permissions, get_tenant_context,
    UserContext, TenantContext
)

router = APIRouter(prefix="/collection", tags=["数据采集"])


# Pydantic模型
class DataPoint(BaseModel):
    """数据点"""
    timestamp: datetime
    value: float
    quality: str = "good"


class DataQueryRequest(BaseModel):
    """数据查询请求"""
    tags: List[str] = Field(..., min_items=1)
    start_time: datetime
    end_time: datetime
    aggregation: Optional[str] = Field("raw", regex="^(raw|mean|sum|min|max)$")
    interval: Optional[str] = None


class DataQueryResponse(BaseModel):
    """数据查询响应"""
    tags: List[str]
    start_time: datetime
    end_time: datetime
    data: Dict[str, List[DataPoint]]


class CollectionStartRequest(BaseModel):
    """启动采集请求"""
    device_ids: Optional[List[str]] = None
    scan_interval: int = Field(default=10, ge=1, le=3600)


class CollectionStatusResponse(BaseModel):
    """采集状态响应"""
    is_running: bool
    device_count: int
    last_data_time: Optional[datetime]
    throughput: float


# 模拟数据采集状态
_collection_status = {
    "is_running": False,
    "devices": {},
    "last_data_time": None
}

# 模拟数据存储
_data_store: Dict[str, List[Dict]] = {}


@router.post("/start")
async def start_collection(
    request: CollectionStartRequest,
    user: UserContext = Depends(require_permissions("device:write")),
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    启动数据采集
    
    启动指定设备的数据采集，如果不指定设备则启动所有设备
    """
    _collection_status["is_running"] = True
    _collection_status["start_time"] = datetime.utcnow()
    
    return {
        "success": True,
        "message": "数据采集已启动",
        "data": {
            "is_running": True,
            "scan_interval": request.scan_interval,
            "started_at": datetime.utcnow().isoformat()
        }
    }


@router.post("/stop")
async def stop_collection(
    device_id: Optional[str] = Query(None),
    user: UserContext = Depends(require_permissions("device:write"))
):
    """
    停止数据采集
    
    停止指定设备或所有设备的数据采集
    """
    _collection_status["is_running"] = False
    
    return {
        "success": True,
        "message": f"数据采集已停止" + (f" (设备: {device_id})" if device_id else ""),
        "data": {"is_running": False}
    }


@router.get("/status", response_model=CollectionStatusResponse)
async def get_collection_status(
    user: UserContext = Depends(require_permissions("device:read"))
):
    """
    获取采集状态
    
    返回当前数据采集的运行状态和统计信息
    """
    # 模拟计算吞吐量
    throughput = 150.5 if _collection_status["is_running"] else 0.0
    
    return CollectionStatusResponse(
        is_running=_collection_status["is_running"],
        device_count=len(_collection_status.get("devices", {})),
        last_data_time=_collection_status.get("last_data_time"),
        throughput=throughput
    )


@router.post("/data/query", response_model=DataQueryResponse)
async def query_data(
    request: DataQueryRequest,
    user: UserContext = Depends(require_permissions("data:read")),
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    查询历史数据
    
    查询指定时间范围和数据点位的历史数据
    """
    result_data = {}
    
    for tag in request.tags:
        # 模拟生成数据
        points = []
        current_time = request.start_time
        
        while current_time <= request.end_time:
            # 模拟正弦波数据
            import math
            base_value = 25.0
            variation = 10.0 * math.sin(current_time.timestamp() / 3600)
            noise = (hash(current_time.isoformat()) % 100) / 100.0 * 2 - 1
            
            points.append(DataPoint(
                timestamp=current_time,
                value=base_value + variation + noise,
                quality="good"
            ))
            
            # 下一个时间点（每分钟）
            current_time += timedelta(minutes=1)
        
        # 如果请求聚合
        if request.aggregation != "raw" and request.interval:
            points = _aggregate_points(points, request.aggregation, request.interval)
        
        result_data[tag] = points
    
    return DataQueryResponse(
        tags=request.tags,
        start_time=request.start_time,
        end_time=request.end_time,
        data=result_data
    )


def _aggregate_points(points: List[DataPoint], aggregation: str, interval: str) -> List[DataPoint]:
    """聚合数据点"""
    # 简化实现：按小时聚合
    from collections import defaultdict
    
    # 解析间隔
    interval_seconds = 3600  # 默认1小时
    if interval.endswith('m'):
        interval_seconds = int(interval[:-1]) * 60
    elif interval.endswith('h'):
        interval_seconds = int(interval[:-1]) * 3600
    
    # 分组
    groups = defaultdict(list)
    for point in points:
        bucket = point.timestamp.replace(minute=0, second=0, microsecond=0)
        groups[bucket].append(point)
    
    # 聚合
    result = []
    for bucket, group_points in sorted(groups.items()):
        values = [p.value for p in group_points]
        
        if aggregation == "mean":
            agg_value = sum(values) / len(values)
        elif aggregation == "sum":
            agg_value = sum(values)
        elif aggregation == "min":
            agg_value = min(values)
        elif aggregation == "max":
            agg_value = max(values)
        else:
            agg_value = sum(values) / len(values)
        
        result.append(DataPoint(
            timestamp=bucket,
            value=round(agg_value, 2),
            quality="good"
        ))
    
    return result


@router.get("/data/latest")
async def get_latest_data(
    tags: Optional[List[str]] = Query(None),
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取最新数据
    
    获取指定点位的最新数据值
    """
    # 如果没有指定tags，返回一些示例数据
    if not tags:
        tags = ["temperature", "pressure", "flow"]
    
    result = {}
    now = datetime.utcnow()
    
    for tag in tags:
        import random
        result[tag] = {
            "timestamp": now.isoformat(),
            "value": round(random.uniform(20.0, 50.0), 2),
            "quality": "good",
            "unit": "°C" if "temp" in tag.lower() else "bar"
        }
    
    return result


@router.get("/data/realtime")
async def get_realtime_data(
    tag: str = Query(..., description="数据点位名称"),
    limit: int = Query(100, ge=1, le=1000),
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取实时数据流
    
    返回最近的数据点用于实时图表展示
    """
    import math
    import random
    
    points = []
    now = datetime.utcnow()
    
    for i in range(limit):
        timestamp = now - timedelta(seconds=limit - i)
        # 模拟实时波动
        base = 30.0
        trend = i / limit * 5
        noise = random.gauss(0, 1)
        
        points.append({
            "timestamp": timestamp.isoformat(),
            "value": round(base + trend + noise, 2),
            "quality": "good"
        })
    
    return {
        "tag": tag,
        "count": len(points),
        "data": points
    }
