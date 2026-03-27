"""
监控大屏路由

作者: Backend Team
职责: 提供大屏展示所需的聚合数据
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class DashboardOverview(BaseModel):
    """大屏概览数据"""
    total_devices: int
    online_devices: int
    offline_devices: int
    total_tags: int
    active_alarms: int
    alarm_count_24h: int
    data_points_24h: int
    system_status: str


class DeviceStatus(BaseModel):
    """设备状态"""
    device_id: str
    device_name: str
    status: str  # online, offline, warning
    last_seen: datetime
    tag_count: int


class RealtimeDataPoint(BaseModel):
    """实时数据点"""
    tag_id: str
    tag_name: str
    value: float
    unit: str
    timestamp: datetime
    status: str  # normal, warning, alarm


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    """
    获取大屏概览数据
    
    包含:
    - 设备统计 (总数/在线/离线)
    - 点位统计
    - 告警统计
    - 系统状态
    """
    # TODO: 从数据库获取真实数据
    return DashboardOverview(
        total_devices=15,
        online_devices=14,
        offline_devices=1,
        total_tags=128,
        active_alarms=3,
        alarm_count_24h=12,
        data_points_24h=1105920,
        system_status="running"
    )


@router.get("/devices", response_model=List[DeviceStatus])
async def get_device_status():
    """获取所有设备状态"""
    # TODO: 从数据库获取真实数据
    return [
        DeviceStatus(
            device_id="DEV_001",
            device_name="1#曝气池",
            status="online",
            last_seen=datetime.now(),
            tag_count=8
        ),
        DeviceStatus(
            device_id="DEV_002",
            device_name="2#曝气池",
            status="online",
            last_seen=datetime.now(),
            tag_count=8
        ),
        DeviceStatus(
            device_id="DEV_003",
            device_name="1#提升泵",
            status="warning",
            last_seen=datetime.now() - timedelta(minutes=5),
            tag_count=4
        )
    ]


@router.get("/realtime", response_model=List[RealtimeDataPoint])
async def get_realtime_data(
    limit: int = Query(20, ge=1, le=100),
    device_id: str = Query(None)
):
    """
    获取实时数据
    
    - **limit**: 返回数据点数量
    - **device_id**: 按设备筛选
    """
    # TODO: 从数据库获取真实数据
    import random
    
    tags = [
        ("TAG_DO_001", "溶解氧", "mg/L", 2.0, 8.0),
        ("TAG_PH_001", "pH值", "", 6.5, 8.5),
        ("TAG_COD_001", "COD", "mg/L", 0, 100),
        ("TAG_TEMP_001", "温度", "°C", 15, 35),
    ]
    
    data = []
    for tag_id, name, unit, min_v, max_v in tags[:limit]:
        value = random.uniform(min_v, max_v)
        status = "normal"
        if value > max_v * 0.9 or value < min_v * 1.1:
            status = "warning"
        
        data.append(RealtimeDataPoint(
            tag_id=tag_id,
            tag_name=name,
            value=round(value, 2),
            unit=unit,
            timestamp=datetime.now(),
            status=status
        ))
    
    return data


@router.get("/trends")
async def get_trend_data(
    tag_id: str,
    hours: int = Query(24, ge=1, le=168)
):
    """
    获取历史趋势数据
    
    - **tag_id**: 点位ID
    - **hours**: 查询小时数
    """
    # TODO: 从 InfluxDB 查询真实数据
    import random
    from datetime import datetime, timedelta
    
    data = []
    now = datetime.now()
    
    for i in range(hours):
        timestamp = now - timedelta(hours=i)
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(random.uniform(2.0, 8.0), 2)
        })
    
    return {"tag_id": tag_id, "data": list(reversed(data))}


@router.get("/alerts/recent")
async def get_recent_alerts(limit: int = Query(10, ge=1, le=50)):
    """获取最近告警"""
    # TODO: 从数据库获取真实数据
    return {
        "alerts": [
            {
                "alert_id": "ALERT_001",
                "rule_name": "缺氧异常",
                "severity": "critical",
                "message": "溶解氧浓度低于 2.0 mg/L",
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False
            }
        ],
        "total": 1
    }
