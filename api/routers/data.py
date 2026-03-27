"""
数据采集路由

作者: Backend Team + Data Team
职责: 数据采集控制、历史数据查询
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DataPoint(BaseModel):
    """数据点"""
    tag_id: str
    value: float
    timestamp: datetime
    quality: str = "good"


class DataCollectionRequest(BaseModel):
    """采集控制请求"""
    action: str  # start, stop, restart
    device_ids: Optional[List[str]] = None


@router.get("/tags")
async def get_all_tags(
    device_id: Optional[str] = None,
    category: Optional[str] = None
):
    """获取所有点位列表"""
    # TODO: 从 TagMapper 获取
    return {
        "tags": [
            {"tag_id": "TAG_DO_001", "name": "溶解氧", "unit": "mg/L", "device": "1#曝气池"},
            {"tag_id": "TAG_PH_001", "name": "pH值", "unit": "", "device": "1#曝气池"},
        ],
        "total": 2
    }


@router.get("/history")
async def get_historical_data(
    tag_id: str,
    start_time: datetime,
    end_time: datetime,
    aggregation: Optional[str] = Query(None, enum=["mean", "max", "min", "count"]),
    interval: Optional[str] = Query(None)  # 1m, 5m, 1h, 1d
):
    """
    查询历史数据
    
    - **tag_id**: 点位ID
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    - **aggregation**: 聚合方式
    - **interval**: 时间间隔
    """
    # TODO: 从 InfluxDB 查询
    return {
        "tag_id": tag_id,
        "data": [],
        "count": 0
    }


@router.post("/collection/control")
async def control_collection(request: DataCollectionRequest):
    """
    控制数据采集
    
    - **action**: start/stop/restart
    - **device_ids**: 指定设备 (为空则控制所有)
    """
    return {"status": "success", "action": request.action}


@router.get("/collection/status")
async def get_collection_status():
    """获取采集状态"""
    return {
        "is_running": True,
        "connected_devices": 14,
        "total_devices": 15,
        "scan_rate": 10,
        "last_scan": datetime.now().isoformat()
    }
