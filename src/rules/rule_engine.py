"""
规则执行引擎
实时评估规则并生成告警
"""

import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

from .rule_parser import RuleParser


class RuleEngine:
    """规则执行引擎"""
    
    def __init__(self, config_file: str, evaluation_interval: int = 10):
        """
        初始化规则引擎
        
        Args:
            config_file: 规则配置文件路径
            evaluation_interval: 规则评估间隔 (秒)
        """
        self.config_file = config_file
        self.evaluation_interval = evaluation_interval
        self.parser = RuleParser()
        
        self.rules: List[Dict[str, Any]] = []
        self.compiled_rules: List[Dict[str, Any]] = []
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()  # 规则加载锁
        
        # 告警抑制 (防止告警风暴)
        self.alert_suppression: Dict[str, datetime] = {}
        self.suppression_window_minutes = 15
        self._suppression_lock = threading.Lock()
        
        # 回调函数
        self.alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._callback_lock = threading.Lock()
        
        self.load_rules()
    
    def load_rules(self):
        """加载并编译规则（线程安全）"""
        with self._lock:
            self.rules = self.parser.parse_rule_file(self.config_file)
            new_compiled_rules = []
            
            for rule in self.rules:
                if not rule.get('enabled', True):
                    continue
                
                try:
                    check_func = self.parser.compile_condition(rule['condition'])
                    
                    compiled_rule = {
                        **rule,
                        'check_func': check_func
                    }
                    new_compiled_rules.append(compiled_rule)
                    
                    logger.debug(f"规则已编译：{rule['name']}")
                    
                except Exception as e:
                    logger.error(f"编译规则 {rule['rule_id']} 失败：{e}")
            
            self.compiled_rules = new_compiled_rules
            
            logger.info(f"规则引擎已加载 {len(self.compiled_rules)} 条有效规则")
    
    def reload_rules(self):
        """重新加载规则 (支持热更新，线程安全)"""
        with self._lock:
            logger.info("重新加载规则...")
            self.load_rules()
    
    def evaluate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        评估所有规则
        
        Args:
            data: 实时数据字典
            
        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        
        for rule in self.compiled_rules:
            try:
                # 执行条件检查
                is_triggered = rule['check_func'](data)
                
                if is_triggered:
                    # 检查告警抑制
                    rule_id = rule['rule_id']
                    now = datetime.now()
                    
                    if self._is_suppressed(rule_id, now):
                        logger.debug(f"规则 {rule_id} 处于抑制期，跳过告警")
                        continue
                    
                    # 生成告警
                    alert = self._create_alert(rule, data)
                    triggered_alerts.append(alert)
                    
                    # 设置抑制时间
                    self._set_suppression(rule_id, now)
                    
                    logger.warning(f"⚠️ 规则触发：{rule['name']} (严重度：{rule.get('severity', 'medium')})")
                    
            except Exception as e:
                logger.error(f"评估规则 {rule.get('rule_id', 'UNKNOWN')} 失败：{e}")
        
        return triggered_alerts
    
    def _is_suppressed(self, rule_id: str, now: datetime) -> bool:
        """检查规则是否处于抑制期（线程安全）"""
        with self._suppression_lock:
            if rule_id not in self.alert_suppression:
                return False
            
            suppression_end = self.alert_suppression[rule_id]
            return now < suppression_end
    
    def _set_suppression(self, rule_id: str, now: datetime):
        """设置规则抑制时间（线程安全）"""
        with self._suppression_lock:
            suppression_end = now + timedelta(minutes=self.suppression_window_minutes)
            self.alert_suppression[rule_id] = suppression_end
    
    def _create_alert(self, rule: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """创建告警对象"""
        return {
            'alert_id': f"ALERT_{rule['rule_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'rule_id': rule['rule_id'],
            'rule_name': rule['name'],
            'description': rule.get('description', ''),
            'severity': rule.get('severity', 'medium'),
            'category': rule.get('category', 'general'),
            'timestamp': datetime.now().isoformat(),
            'suggested_actions': rule.get('suggested_actions', []),
            'escalation': rule.get('escalation', {}),
            'data_snapshot': self._extract_relevant_data(data, rule),
            'acknowledged': False,
            'acknowledged_by': None,
            'acknowledged_at': None
        }
    
    def _extract_relevant_data(self, data: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """提取与规则相关的数据快照"""
        snapshot = {}
        
        # 从条件中提取涉及的指标
        condition = rule.get('condition', {})
        metrics = self._extract_metrics_from_condition(condition)
        
        for metric in metrics:
            if metric in data:
                snapshot[metric] = data[metric]
        
        return snapshot
    
    def _extract_metrics_from_condition(self, condition: Dict[str, Any]) -> List[str]:
        """从条件中提取指标名称"""
        metrics = []
        
        if 'metric' in condition:
            metrics.append(condition['metric'])
        
        if 'conditions' in condition:  # 逻辑组合条件
            for sub_cond in condition['conditions']:
                metrics.extend(self._extract_metrics_from_condition(sub_cond))
        
        if 'metrics' in condition:  # 相关性条件
            metrics.extend(condition['metrics'])
        
        return list(set(metrics))  # 去重
    
    def start_continuous_evaluation(self, data_provider: Callable[[], Dict[str, Any]]):
        """
        启动连续评估
        
        Args:
            data_provider: 数据提供函数，返回实时数据字典
        """
        if self._running:
            logger.warning("规则引擎已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._evaluation_loop,
            args=(data_provider,),
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"规则引擎已启动 (评估间隔：{self.evaluation_interval}秒)")
    
    def _evaluation_loop(self, data_provider: Callable[[], Dict[str, Any]]):
        """评估循环"""
        while self._running:
            try:
                # 获取实时数据
                data = data_provider()
                
                # 评估规则
                alerts = self.evaluate(data)
                
                # 触发告警回调
                if alerts:
                    for callback in self.alert_callbacks:
                        try:
                            callback(alerts)
                        except Exception as e:
                            logger.error(f"告警回调执行失败：{e}")
                
                time.sleep(self.evaluation_interval)
                
            except Exception as e:
                logger.error(f"规则评估循环出错：{e}")
                time.sleep(5)
    
    def stop_evaluation(self):
        """停止连续评估"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("规则引擎已停止")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加告警回调函数（线程安全）"""
        with self._callback_lock:
            self.alert_callbacks.append(callback)
    
    def _execute_callbacks(self, alert: Dict[str, Any]):
        """执行回调函数（带异常处理）"""
        with self._callback_lock:
            callbacks = self.alert_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调函数执行失败：{e}")
    
    def acknowledge_alert(self, alert_id: str, operator: str):
        """
        确认告警
        
        Args:
            alert_id: 告警 ID
            operator: 操作员姓名
        """
        # 这里可以维护一个活动告警列表
        # 简化实现：仅记录日志
        logger.info(f"告警 {alert_id} 已被 {operator} 确认")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取当前活动告警 (简化实现)"""
        # 实际应用中需要维护一个活动告警列表
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取规则引擎统计信息"""
        return {
            'total_rules': len(self.rules),
            'enabled_rules': len(self.compiled_rules),
            'suppression_window_minutes': self.suppression_window_minutes,
            'active_suppressions': len(self.alert_suppression),
            'is_running': self._running
        }


# 使用示例
if __name__ == "__main__":
    # 初始化规则引擎
    engine = RuleEngine('config/rules.json', evaluation_interval=5)
    
    # 模拟数据提供函数
    def get_realtime_data():
        import random
        return {
            'TAG_DO_001': random.uniform(1.0, 5.0),
            'TAG_PH_001': random.uniform(6.0, 8.0),
            'TAG_COD_001': random.uniform(50, 150),
            '_history': {
                'TAG_DO_001': [random.uniform(1.0, 5.0) for _ in range(20)]
            }
        }
    
    # 告警回调函数
    def on_alerts_triggered(alerts):
        print(f"\n🚨 触发 {len(alerts)} 个告警:")
        for alert in alerts:
            print(f"  [{alert['severity'].upper()}] {alert['rule_name']}")
            print(f"    建议措施：{alert['suggested_actions'][:2]}")
    
    engine.register_alert_callback(on_alerts_triggered)
    
    # 启动连续评估
    engine.start_continuous_evaluation(get_realtime_data)
    
    # 运行 30 秒
    time.sleep(30)
    
    # 查看统计信息
    stats = engine.get_statistics()
    print(f"\n统计信息：{stats}")
    
    # 停止
    engine.stop_evaluation()
