"""
告警升级模块

功能需求: R-07 告警升级 - 长时间未处理自动升级
作者: Backend Team
"""

import json
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger


class EscalationLevel(Enum):
    """升级级别"""
    L1 = "level_1"      # 一线运维
    L2 = "level_2"      # 二线专家
    L3 = "level_3"      # 管理层
    L4 = "emergency"    # 紧急响应


@dataclass
class EscalationRule:
    """升级规则"""
    level: EscalationLevel
    timeout_minutes: int
    notify_channels: List[str]
    notify_targets: List[str]
    message_template: str
    auto_actions: List[str]


@dataclass
class EscalationRecord:
    """升级记录"""
    alert_id: str
    current_level: EscalationLevel
    created_at: datetime
    last_escalation_at: datetime
    escalation_count: int
    notified_targets: List[str]
    acknowledged: bool
    acknowledged_by: Optional[str]


class EscalationEngine:
    """
    告警升级引擎
    
    功能:
    1. 监控未确认告警
    2. 按时间自动升级
    3. 多渠道通知
    4. 升级历史记录
    """
    
    # 默认升级规则
    DEFAULT_RULES = {
        EscalationLevel.L1: EscalationRule(
            level=EscalationLevel.L1,
            timeout_minutes=15,
            notify_channels=["web", "app"],
            notify_targets=["oncall_l1"],
            message_template="告警 {alert_name} 已产生 {timeout} 分钟，请尽快处理",
            auto_actions=[]
        ),
        EscalationLevel.L2: EscalationRule(
            level=EscalationLevel.L2,
            timeout_minutes=30,
            notify_channels=["sms", "phone", "feishu"],
            notify_targets=["oncall_l2", "team_lead"],
            message_template="⚠️ 告警升级: {alert_name} 已持续 {timeout} 分钟未处理，已升级到二线",
            auto_actions=["create_ticket"]
        ),
        EscalationLevel.L3: EscalationRule(
            level=EscalationLevel.L3,
            timeout_minutes=60,
            notify_channels=["phone", "email", "dingtalk"],
            notify_targets=["manager", "director"],
            message_template="🚨 紧急告警: {alert_name} 已持续 {timeout} 分钟未处理，请立即关注",
            auto_actions=["create_ticket", "notify_management"]
        ),
        EscalationLevel.L4: EscalationRule(
            level=EscalationLevel.L4,
            timeout_minutes=120,
            notify_channels=["phone", "sms", "all"],
            notify_targets=["emergency_team", "cto"],
            message_template="🔥 紧急升级: {alert_name} 已持续 {timeout} 分钟，启动紧急响应流程",
            auto_actions=["create_ticket", "escalate_emergency", "auto_remediation"]
        )
    }
    
    def __init__(self, custom_rules: Optional[Dict] = None):
        """
        初始化升级引擎
        
        Args:
            custom_rules: 自定义升级规则
        """
        self.rules = custom_rules or self.DEFAULT_RULES
        self.active_escalations: Dict[str, EscalationRecord] = {}
        self._callbacks: List[Callable] = []
        self._running = False
        self._check_task = None
        
        logger.info("告警升级引擎已初始化")
    
    def register_callback(self, callback: Callable[[str, EscalationLevel, dict], None]):
        """
        注册升级回调函数
        
        Args:
            callback: 回调函数(alert_id, level, context)
        """
        self._callbacks.append(callback)
    
    def start_tracking(self, alert: dict):
        """
        开始跟踪告警
        
        Args:
            alert: 告警信息
        """
        alert_id = alert['alert_id']
        
        if alert_id in self.active_escalations:
            return
        
        now = datetime.now()
        record = EscalationRecord(
            alert_id=alert_id,
            current_level=EscalationLevel.L1,
            created_at=now,
            last_escalation_at=now,
            escalation_count=0,
            notified_targets=[],
            acknowledged=False,
            acknowledged_by=None
        )
        
        self.active_escalations[alert_id] = record
        
        logger.info(f"开始跟踪告警 {alert_id}")
        
        # 立即执行L1通知
        self._execute_escalation(record, alert)
    
    def acknowledge(self, alert_id: str, user: str):
        """
        确认告警，停止升级
        
        Args:
            alert_id: 告警ID
            user: 确认用户
        """
        if alert_id not in self.active_escalations:
            return
        
        record = self.active_escalations[alert_id]
        record.acknowledged = True
        record.acknowledged_by = user
        
        # 从跟踪列表移除
        del self.active_escalations[alert_id]
        
        logger.info(f"告警 {alert_id} 已被 {user} 确认，停止升级")
    
    async def start_monitoring(self, check_interval: int = 60):
        """
        启动监控循环
        
        Args:
            check_interval: 检查间隔(秒)
        """
        self._running = True
        
        while self._running:
            try:
                self._check_escalations()
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"升级检查失败: {e}")
                await asyncio.sleep(10)
    
    def _check_escalations(self):
        """检查所有跟踪中的告警是否需要升级"""
        now = datetime.now()
        
        for alert_id, record in list(self.active_escalations.items()):
            if record.acknowledged:
                continue
            
            # 计算当前持续时间
            duration = (now - record.created_at).total_seconds() / 60
            
            # 确定应该处于哪个级别
            target_level = self._determine_level(duration)
            
            # 如果需要升级
            if target_level.value > record.current_level.value:
                # 获取告警信息（这里简化处理，实际应从告警管理器获取）
                alert_info = self._get_alert_info(alert_id)
                
                if alert_info:
                    # 执行升级
                    record.current_level = target_level
                    record.last_escalation_at = now
                    record.escalation_count += 1
                    
                    self._execute_escalation(record, alert_info)
                    
                    logger.warning(
                        f"告警 {alert_id} 升级到 {target_level.name}, "
                        f"已持续 {duration:.0f} 分钟"
                    )
    
    def _determine_level(self, duration_minutes: float) -> EscalationLevel:
        """根据持续时间确定升级级别"""
        for level in [EscalationLevel.L4, EscalationLevel.L3, 
                      EscalationLevel.L2, EscalationLevel.L1]:
            rule = self.rules[level]
            if duration_minutes >= rule.timeout_minutes:
                return level
        
        return EscalationLevel.L1
    
    def _execute_escalation(self, record: EscalationRecord, alert: dict):
        """执行升级操作"""
        level = record.current_level
        rule = self.rules[level]
        
        # 构建通知内容
        duration = (datetime.now() - record.created_at).total_seconds() / 60
        
        message = rule.message_template.format(
            alert_name=alert.get('rule_name', 'Unknown'),
            alert_id=record.alert_id,
            timeout=int(duration),
            severity=alert.get('severity', 'unknown'),
            device=alert.get('device', 'unknown')
        )
        
        context = {
            'alert': alert,
            'level': level.name,
            'duration_minutes': duration,
            'message': message,
            'channels': rule.notify_channels,
            'targets': rule.notify_targets,
            'auto_actions': rule.auto_actions
        }
        
        # 记录已通知目标
        record.notified_targets.extend(rule.notify_targets)
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(record.alert_id, level, context)
            except Exception as e:
                logger.error(f"升级回调执行失败: {e}")
        
        # 执行自动操作
        for action in rule.auto_actions:
            self._execute_auto_action(action, alert, context)
    
    def _execute_auto_action(self, action: str, alert: dict, context: dict):
        """执行自动操作"""
        logger.info(f"执行自动操作: {action}")
        
        if action == "create_ticket":
            # 自动创建工单
            self._create_ticket(alert, context)
        elif action == "notify_management":
            # 通知管理层
            pass
        elif action == "escalate_emergency":
            # 启动紧急响应
            pass
        elif action == "auto_remediation":
            # 尝试自动修复
            pass
    
    def _create_ticket(self, alert: dict, context: dict):
        """创建工单（简化实现）"""
        ticket_info = {
            'title': f"[自动创建] {alert.get('rule_name', 'Unknown')}",
            'description': context['message'],
            'severity': alert.get('severity', 'medium'),
            'source_alert_id': alert.get('alert_id'),
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"自动创建工单: {ticket_info}")
        # TODO: 调用工单系统API
    
    def _get_alert_info(self, alert_id: str) -> Optional[dict]:
        """获取告警信息（简化实现）"""
        # 实际应用中应从告警管理器获取
        return {
            'alert_id': alert_id,
            'rule_name': '缺氧异常',
            'severity': 'critical',
            'device': '1#曝气池'
        }
    
    def get_escalation_history(self, alert_id: str) -> List[dict]:
        """获取告警升级历史"""
        # TODO: 实现历史记录查询
        return []
    
    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        logger.info("告警升级引擎已停止")


class EscalationNotifier:
    """
    升级通知器
    
    支持多种通知渠道
    """
    
    def __init__(self):
        self._channels = {}
    
    def register_channel(self, name: str, handler: Callable):
        """注册通知渠道"""
        self._channels[name] = handler
    
    async def notify(self, channels: List[str], targets: List[str], message: str):
        """
        发送通知
        
        Args:
            channels: 渠道列表 (web/sms/phone/email/feishu/dingtalk)
            targets: 目标用户/组
            message: 消息内容
        """
        for channel in channels:
            if channel in self._channels:
                try:
                    await self._channels[channel](targets, message)
                    logger.info(f"通知已发送: {channel} -> {targets}")
                except Exception as e:
                    logger.error(f"通知发送失败 [{channel}]: {e}")
            else:
                logger.warning(f"未注册的通知渠道: {channel}")


# 使用示例
if __name__ == "__main__":
    # 创建升级引擎
    engine = EscalationEngine()
    
    # 注册通知回调
    def on_escalation(alert_id: str, level: EscalationLevel, context: dict):
        print(f"\n🚨 告警升级通知")
        print(f"  告警ID: {alert_id}")
        print(f"  升级级别: {level.name}")
        print(f"  消息: {context['message']}")
        print(f"  通知渠道: {context['channels']}")
        print(f"  通知目标: {context['targets']}")
    
    engine.register_callback(on_escalation)
    
    # 模拟告警
    test_alert = {
        'alert_id': 'ALERT_001',
        'rule_name': '缺氧异常',
        'severity': 'critical',
        'device': '1#曝气池'
    }
    
    # 开始跟踪
    engine.start_tracking(test_alert)
    
    print("升级引擎已启动，模拟运行...")
    print("(按 Ctrl+C 停止)")
    
    # 模拟运行
    try:
        asyncio.run(engine.start_monitoring(check_interval=10))
    except KeyboardInterrupt:
        engine.stop_monitoring()
        print("\n已停止")
