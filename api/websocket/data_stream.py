"""
WebSocket 数据流管理

作者: Backend Team
职责: 管理 WebSocket 连接，推送实时数据
"""

import asyncio
import json
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket
from loguru import logger


class DataStreamManager:
    """
    WebSocket 数据流管理器
    
    功能:
    - 管理客户端连接
    - 推送实时数据
    - 处理订阅控制
    - 心跳检测
    """
    
    def __init__(self):
        # 活跃连接
        self.active_connections: Set[WebSocket] = set()
        
        # 订阅管理: websocket -> {tags: set, devices: set}
        self.subscriptions: Dict[WebSocket, Dict[str, Set[str]]] = {}
        
        # 运行状态
        self._running = False
        self._broadcast_task = None
        
    async def start(self):
        """启动广播任务"""
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("WebSocket 数据流管理器已启动")
    
    async def stop(self):
        """停止广播任务"""
        self._running = False
        
        # 关闭所有连接
        for websocket in list(self.active_connections):
            await self.disconnect(websocket)
        
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket 数据流管理器已停止")
    
    async def connect(self, websocket: WebSocket):
        """
        接受新连接
        
        Args:
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = {
            "tags": set(),
            "devices": set()
        }
        
        logger.info(f"新的 WebSocket 连接，当前连接数: {len(self.active_connections)}")
        
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "连接成功",
            "timestamp": datetime.now().isoformat()
        })
    
    async def disconnect(self, websocket: WebSocket):
        """
        断开连接
        
        Args:
            websocket: WebSocket 连接对象
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        
        try:
            await websocket.close()
        except:
            pass
        
        logger.info(f"WebSocket 连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def handle_message(self, websocket: WebSocket, message: dict):
        """
        处理客户端消息
        
        支持的命令:
        - subscribe_tags: 订阅点位
        - unsubscribe_tags: 取消订阅点位
        - subscribe_devices: 订阅设备
        - ping: 心跳
        """
        msg_type = message.get("type")
        
        if msg_type == "subscribe_tags":
            tags = set(message.get("tags", []))
            self.subscriptions[websocket]["tags"].update(tags)
            await websocket.send_json({
                "type": "subscribed",
                "tags": list(self.subscriptions[websocket]["tags"])
            })
            
        elif msg_type == "unsubscribe_tags":
            tags = set(message.get("tags", []))
            self.subscriptions[websocket]["tags"].difference_update(tags)
            await websocket.send_json({
                "type": "unsubscribed",
                "tags": list(self.subscriptions[websocket]["tags"])
            })
            
        elif msg_type == "subscribe_devices":
            devices = set(message.get("devices", []))
            self.subscriptions[websocket]["devices"].update(devices)
            await websocket.send_json({
                "type": "subscribed",
                "devices": list(self.subscriptions[websocket]["devices"])
            })
            
        elif msg_type == "ping":
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            })
            
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"未知命令: {msg_type}"
            })
    
    async def _broadcast_loop(self):
        """广播循环"""
        while self._running:
            try:
                # 获取实时数据 (模拟)
                data = await self._fetch_realtime_data()
                
                # 推送给所有订阅的客户端
                await self._broadcast_data(data)
                
                # 等待下一次广播
                await asyncio.sleep(5)  # 每 5 秒广播一次
                
            except Exception as e:
                logger.error(f"广播循环错误: {e}")
                await asyncio.sleep(5)
    
    async def _fetch_realtime_data(self) -> Dict:
        """
        获取实时数据
        
        实际应用应从数据采集服务或消息队列获取
        """
        import random
        
        # 模拟数据
        return {
            "TAG_DO_001": {
                "value": round(random.uniform(2.0, 8.0), 2),
                "unit": "mg/L",
                "timestamp": datetime.now().isoformat()
            },
            "TAG_PH_001": {
                "value": round(random.uniform(6.5, 8.5), 2),
                "unit": "",
                "timestamp": datetime.now().isoformat()
            },
            "TAG_COD_001": {
                "value": round(random.uniform(50, 150), 2),
                "unit": "mg/L",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def _broadcast_data(self, data: Dict):
        """
        广播数据给订阅的客户端
        
        Args:
            data: 实时数据字典
        """
        for websocket in list(self.active_connections):
            try:
                subscription = self.subscriptions.get(websocket, {})
                subscribed_tags = subscription.get("tags", set())
                
                # 过滤数据
                filtered_data = {}
                for tag_id, value in data.items():
                    if not subscribed_tags or tag_id in subscribed_tags:
                        filtered_data[tag_id] = value
                
                if filtered_data:
                    await websocket.send_json({
                        "type": "data",
                        "payload": filtered_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"发送数据失败: {e}")
                # 移除失效连接
                await self.disconnect(websocket)
    
    async def broadcast_alert(self, alert: Dict):
        """
        广播告警给所有客户端
        
        Args:
            alert: 告警数据
        """
        message = {
            "type": "alert",
            "payload": alert,
            "timestamp": datetime.now().isoformat()
        }
        
        for websocket in list(self.active_connections):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送告警失败: {e}")
                await self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)
