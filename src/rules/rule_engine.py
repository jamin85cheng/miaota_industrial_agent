"""
规则执行引擎
实时评估数据，触发规则，生成标签和告警
"""

import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .rule_parser import RuleParser


class RuleEngine:
    """规则执行引擎"""
    
    def __init__(self, rules_file: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化规则引擎
        
        Args:
            rules_file: JSON 规则文件路径
            config: 额外配置参数
        """
        self.rules_file = rules_file
        self.config = config or {}
        
        self.parser = RuleParser()
        self.rules: List[Dict[str, Any]] = []
        
        # 告警抑制缓存：rule_id → 上次告警时间
        self.alert_suppression: Dict[str, datetime] = {}
        
        # 历史数据缓存 (用于持续时间判断)
        self.history_buffer: Dict[str, pd.DataFrame] = {}
        self.buffer_size_minutes = 60  # 保留 60 分钟历史数据
        
        # 线程池 (并行执行规则)
        max_workers = self.config.get('max_workers', 4)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        self.load_rules()
        logger.info(f"RuleEngine 初始化完成，加载 {len(self.rules)} 条规则")
    
    def load_rules(self):
        """加载规则"""
        self.rules = self.parser.parse_file(self.rules_file)
        logger.info(f"重新加载规则完成，共 {len(self.rules)} 条")
    
    def evaluate(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        评估当前数据，返回触发的规则和标签
        
        Args:
            data: DataFrame，索引为时间，列为各指标值
            
        Returns:
            触发的规则列表，包含标签、建议动作等
        """
        triggered_rules = []
        
        # 更新历史数据缓冲区
        self._update_history_buffer(data)
        
        # 并行执行所有规则
        futures = {}
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            future = self.executor.submit(self._evaluate_single_rule, rule, data)
            futures[future] = rule
        
        # 收集结果
        for future in as_completed(futures):
            rule = futures[future]
            try:
                result = future.result(timeout=30)  # 单条规则超时 30 秒
                if result:
                    # 检查告警抑制
                    if not self._is_suppressed(rule['rule_id']):
                        triggered_rules.append(result)
                        # 记录告警时间
                        self.alert_suppression[rule['rule_id']] = datetime.now()
                        logger.warning(f"规则触发：{rule['rule_id']} - {rule['name']}")
            except Exception as e:
                logger.error(f"规则执行失败 {rule['rule_id']}: {e}")
        
        return triggered_rules
    
    def _evaluate_single_rule(self, rule: Dict[str, Any], data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        评估单条规则
        
        Returns:
            如果触发则返回结果字典，否则返回 None
        """
        try:
            executor = rule.get('executor')
            if not executor:
                return None
            
            # 根据条件类型提供不同的数据视图
            condition_type = rule.get('condition_type', 'threshold')
            
            if condition_type in ['duration', 'rate_of_change', 'logic', 'correlation_violation']:
                # 需要历史数据的规则使用完整 DataFrame
                eval_data = self._get_history_data(rule)
            else:
                # 阈值判断只需最新数据点
                eval_data = data.iloc[-1] if len(data) > 0 else pd.Series()
            
            # 执行判断
            is_triggered = executor(eval_data)
            
            if is_triggered:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'rule_id': rule['rule_id'],
                    'name': rule['name'],
                    'label': rule['label'],
                    'severity': rule['severity'],
                    'category': rule['category'],
                    'description': rule['description'],
                    'suggested_actions': rule['suggested_actions'],
                    'escalation': rule.get('escalation', {}),
                    'data_snapshot': self._capture_snapshot(data)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"规则评估错误 {rule['rule_id']}: {e}")
            return None
    
    def _get_history_data(self, rule: Dict[str, Any]) -> pd.DataFrame:
        """获取规则所需的历史数据"""
        # 简单实现：返回所有历史数据
        # 实际应该根据规则需要的指标和时间范围精确提取
        all_history = pd.concat(self.history_buffer.values()) if self.history_buffer else pd.DataFrame()
        return all_history.tail(1000)  # 最多返回最近 1000 个点
    
    def _update_history_buffer(self, new_data: pd.DataFrame):
        """更新历史数据缓冲区"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加时间戳列
        new_data = new_data.copy()
        new_data['timestamp'] = timestamp
        
        # 追加到缓冲区
        for col in new_data.columns:
            if col == 'timestamp':
                continue
            
            if col not in self.history_buffer:
                self.history_buffer[col] = pd.DataFrame(columns=[col, 'timestamp'])
            
            # 追加新数据
            new_row = pd.DataFrame({col: [new_data[col].iloc[-1]], 'timestamp': [timestamp]})
            self.history_buffer[col] = pd.concat([self.history_buffer[col], new_row], ignore_index=True)
        
        # 清理过期数据 (保留最近 60 分钟)
        cutoff_time = datetime.now() - timedelta(minutes=self.buffer_size_minutes)
        for col in self.history_buffer:
            df = self.history_buffer[col]
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                self.history_buffer[col] = df[df['timestamp'] > cutoff_time]
    
    def _is_suppressed(self, rule_id: str) -> bool:
        """检查规则是否在抑制期内"""
        suppression_window = self.config.get('suppression_window_minutes', 15)
        
        if rule_id not in self.alert_suppression:
            return False
        
        last_alert = self.alert_suppression[rule_id]
        time_since_last = datetime.now() - last_alert
        
        return time_since_last < timedelta(minutes=suppression_window)
    
    def _capture_snapshot(self, data: pd.DataFrame) -> Dict[str, Any]:
        """捕获当前数据快照"""
        if len(data) == 0:
            return {}
        
        latest = data.iloc[-1]
        snapshot = {}
        
        for col in data.columns:
            value = latest[col] if col in latest.index else None
            snapshot[col] = {
                'value': value,
                'unit': ''  # 可以从 tag_mapping 获取单位
            }
        
        return snapshot
    
    def get_all_labels(self) -> List[str]:
        """获取所有可能的标签"""
        return list(set(rule['label'] for rule in self.rules))
    
    def get_rules_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按类别获取规则"""
        return [rule for rule in self.rules if rule.get('category') == category]
    
    def get_rules_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """按严重程度获取规则"""
        return [rule for rule in self.rules if rule.get('severity') == severity]
    
    def reload_rules(self):
        """重新加载规则 (支持热更新)"""
        logger.info("重新加载规则...")
        self.load_rules()
    
    def add_rule(self, rule_config: Dict[str, Any]):
        """动态添加规则"""
        parsed_rule = self.parser.parse(rule_config)
        self.rules.append(parsed_rule)
        logger.info(f"添加新规则：{parsed_rule['rule_id']}")
    
    def remove_rule(self, rule_id: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r['rule_id'] != rule_id]
        logger.info(f"移除规则：{rule_id}")
    
    def enable_rule(self, rule_id: str):
        """启用规则"""
        for rule in self.rules:
            if rule['rule_id'] == rule_id:
                rule['enabled'] = True
                logger.info(f"启用规则：{rule_id}")
                break
    
    def disable_rule(self, rule_id: str):
        """禁用规则"""
        for rule in self.rules:
            if rule['rule_id'] == rule_id:
                rule['enabled'] = False
                logger.info(f"禁用规则：{rule_id}")
                break


# 使用示例
if __name__ == "__main__":
    # 初始化规则引擎
    engine = RuleEngine('config/rules.json')
    
    # 模拟实时数据
    data = pd.DataFrame({
        'TAG_DO_001': [1.5, 1.4, 1.3, 1.2, 1.1],  # DO 持续下降
        'TAG_PH_001': [7.2, 7.1, 7.0, 6.9, 6.8],
        'TAG_COD_001': [80, 85, 90, 95, 105],     # COD 超标
        'TAG_Pump_001_Status': [True, True, True, True, True],
        'TAG_Flow_001': [120, 118, 115, 110, 5],  # 流量突降
    })
    
    # 评估规则
    triggered = engine.evaluate(data)
    
    print(f"\n触发了 {len(triggered)} 条规则:")
    for alert in triggered:
        print(f"\n⚠️  [{alert['severity'].upper()}] {alert['name']}")
        print(f"   标签：{alert['label']}")
        print(f"   建议动作:")
        for action in alert['suggested_actions']:
            print(f"     - {action}")
