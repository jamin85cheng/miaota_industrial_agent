"""
规则 DSL 解析器
将 JSON 格式的规则定义转换为可执行的条件判断
"""

import json
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from loguru import logger
import pandas as pd


class RuleParser:
    """规则解析器 - 支持多种条件类型"""
    
    def __init__(self):
        self.operators = {
            '>': lambda x, y: x > y,
            '>=': lambda x, y: x >= y,
            '<': lambda x, y: x < y,
            '<=': lambda x, y: x <= y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
        }
    
    def parse(self, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析规则配置
        
        Args:
            rule_config: 单条规则的 JSON 配置
            
        Returns:
            包含解析后条件的字典
        """
        rule_id = rule_config.get('rule_id', 'UNKNOWN')
        condition = rule_config.get('condition', {})
        condition_type = condition.get('type', 'threshold')
        
        parsed_rule = {
            'rule_id': rule_id,
            'name': rule_config.get('name', ''),
            'description': rule_config.get('description', ''),
            'enabled': rule_config.get('enabled', True),
            'condition_type': condition_type,
            'severity': rule_config.get('severity', 'medium'),
            'label': rule_config.get('label', '未知异常'),
            'category': rule_config.get('category', 'general'),
            'suggested_actions': rule_config.get('suggested_actions', []),
            'escalation': rule_config.get('escalation', {}),
            'executor': self._get_executor(condition_type, condition)
        }
        
        return parsed_rule
    
    def _get_executor(self, condition_type: str, condition: Dict[str, Any]) -> Callable:
        """根据条件类型获取执行函数"""
        
        if condition_type == 'threshold':
            return self._create_threshold_executor(condition)
        
        elif condition_type == 'duration':
            return self._create_duration_executor(condition)
        
        elif condition_type == 'rate_of_change':
            return self._create_rate_of_change_executor(condition)
        
        elif condition_type == 'logic':
            return self._create_logic_executor(condition)
        
        elif condition_type == 'correlation_violation':
            return self._create_correlation_executor(condition)
        
        else:
            logger.warning(f"未知的条件类型：{condition_type}，使用阈值判断")
            return self._create_threshold_executor(condition)
    
    def _create_threshold_executor(self, condition: Dict[str, Any]) -> Callable:
        """创建阈值判断执行器"""
        metric = condition.get('metric')
        operator_str = condition.get('operator', '>')
        threshold = condition.get('threshold', 0)
        
        operator_func = self.operators.get(operator_str)
        if not operator_func:
            raise ValueError(f"不支持的运算符：{operator_str}")
        
        def executor(data: pd.Series) -> bool:
            if metric not in data.index:
                return False
            current_value = data[metric]
            return operator_func(current_value, threshold)
        
        return executor
    
    def _create_duration_executor(self, condition: Dict[str, Any]) -> Callable:
        """创建持续时间判断执行器"""
        metric = condition.get('metric')
        operator_str = condition.get('operator', '<')
        threshold = condition.get('threshold', 0)
        duration_minutes = condition.get('duration_minutes', 10)
        
        operator_func = self.operators.get(operator_str)
        
        def executor(data: pd.DataFrame) -> bool:
            """
            data: DataFrame，索引为时间，列为各指标
            需要检查持续时间内是否一直满足条件
            """
            if metric not in data.columns:
                return False
            
            # 判断每个点是否满足条件
            series = data[metric]
            if operator_str == '<':
                violation = series < threshold
            elif operator_str == '>':
                violation = series > threshold
            elif operator_str == '==':
                violation = series == threshold
            else:
                violation = operator_func(series, threshold)
            
            # 计算需要的连续点数 (假设数据频率为 10 秒/点)
            # 实际应该根据数据采集频率动态计算
            points_per_minute = 6  # 10 秒一个点
            required_points = int(duration_minutes * points_per_minute)
            
            # 使用 rolling window 检查是否有连续满足条件的情况
            continuous_violation = violation.rolling(window=required_points, min_periods=required_points).sum()
            
            return (continuous_violation == required_points).any()
        
        return executor
    
    def _create_rate_of_change_executor(self, condition: Dict[str, Any]) -> Callable:
        """创建变化率判断执行器"""
        metric = condition.get('metric')
        change_threshold = condition.get('change_threshold', 10)
        window_minutes = condition.get('window_minutes', 5)
        
        def executor(data: pd.DataFrame) -> bool:
            if metric not in data.columns:
                return False
            
            series = data[metric]
            
            # 计算窗口内的变化量
            points_per_minute = 6  # 假设 10 秒一个点
            window_points = int(window_minutes * points_per_minute)
            
            if len(series) < window_points:
                return False
            
            # 计算当前值与 window_minutes 前的差值
            diff = series.diff(window_points)
            
            # 判断变化量是否超过阈值
            return (diff.abs() > change_threshold).any()
        
        return executor
    
    def _create_logic_executor(self, condition: Dict[str, Any]) -> Callable:
        """创建逻辑组合判断执行器"""
        sub_conditions = condition.get('conditions', [])
        logic = condition.get('logic', 'AND')
        duration_minutes = condition.get('duration_minutes', 0)
        
        # 递归解析子条件
        sub_executors = []
        for sub_cond in sub_conditions:
            sub_executor = self._create_threshold_executor(sub_cond)
            sub_executors.append(sub_executor)
        
        def executor(data: pd.DataFrame) -> bool:
            if not sub_executors:
                return False
            
            # 对每个时间点进行评估
            results = []
            timestamps = data.index
            
            for ts in timestamps:
                point_data = data.loc[ts:ts]  # 单行 DataFrame
                single_results = [exec(point_data.squeeze()) for exec in sub_executors]
                
                if logic == 'AND':
                    result = all(single_results)
                elif logic == 'OR':
                    result = any(single_results)
                else:
                    result = all(single_results)
                
                results.append(result)
            
            # 如果需要持续时间判断
            if duration_minutes > 0:
                results_series = pd.Series(results, index=timestamps)
                points_per_minute = 6
                required_points = int(duration_minutes * points_per_minute)
                continuous = results_series.rolling(window=required_points, min_periods=required_points).sum()
                return (continuous == required_points).any()
            else:
                return any(results)
        
        return executor
    
    def _create_correlation_executor(self, condition: Dict[str, Any]) -> Callable:
        """创建相关性违背判断执行器"""
        metrics = condition.get('metrics', [])
        expected_correlation = condition.get('expected_correlation', 'positive')
        violation_duration = condition.get('violation_duration_minutes', 15)
        
        def executor(data: pd.DataFrame) -> bool:
            if len(metrics) < 2:
                return False
            
            # 确保所有指标都存在
            for m in metrics:
                if m not in data.columns:
                    return False
            
            # 计算滚动相关性
            window_size = 10  # 使用最近 10 个点计算相关性
            if len(data) < window_size:
                return False
            
            # 计算两个指标的相关性
            metric1, metric2 = metrics[0], metrics[1]
            rolling_corr = data[metric1].rolling(window=window_size).corr(data[metric2])
            
            # 判断是否违背预期相关性
            if expected_correlation == 'positive':
                violation = rolling_corr < 0  # 应为正相关但变为负相关
            elif expected_correlation == 'negative':
                violation = rolling_corr > 0  # 应为负相关但变为正相关
            else:
                violation = pd.Series([False] * len(data))
            
            # 检查持续时间
            if violation_duration > 0:
                points_per_minute = 6
                required_points = int(violation_duration * points_per_minute)
                continuous = violation.rolling(window=required_points, min_periods=required_points).sum()
                return (continuous == required_points).any()
            
            return violation.any()
        
        return executor
    
    def parse_file(self, rules_file: str) -> List[Dict[str, Any]]:
        """
        从文件解析所有规则
        
        Args:
            rules_file: JSON 规则文件路径
            
        Returns:
            解析后的规则列表
        """
        rules_path = Path(rules_file)
        if not rules_path.exists():
            logger.error(f"规则文件不存在：{rules_path}")
            return []
        
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
        
        rules_list = rules_data.get('rules', [])
        parsed_rules = []
        
        for rule_config in rules_list:
            try:
                parsed_rule = self.parse(rule_config)
                parsed_rules.append(parsed_rule)
                logger.debug(f"解析规则：{parsed_rule['rule_id']} - {parsed_rule['name']}")
            except Exception as e:
                logger.error(f"解析规则失败 {rule_config.get('rule_id', 'UNKNOWN')}: {e}")
        
        logger.info(f"成功解析 {len(parsed_rules)} 条规则")
        return parsed_rules


# 使用示例
if __name__ == "__main__":
    parser = RuleParser()
    rules = parser.parse_file('config/rules.json')
    
    print(f"\n解析了 {len(rules)} 条规则:")
    for rule in rules[:3]:  # 只显示前 3 条
        print(f"  - {rule['rule_id']}: {rule['name']} ({rule['condition_type']})")
