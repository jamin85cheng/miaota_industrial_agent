"""
标签工厂模块

功能：
- 自动生成数据标签 (正常/异常/故障类型)
- 基于规则的标签生成
- 基于聚类的无监督标签生成
- 标签质量评估
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from sklearn.cluster import DBSCAN, KMeans
from loguru import logger


class LabelFactory:
    """标签工厂"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.label_mapping = {}  # 标签编码映射
        self.rules = []  # 标签规则
    
    def add_rule(self, rule: Dict[str, Any]):
        """添加标签规则"""
        self.rules.append(rule)
        logger.debug(f"添加标签规则：{rule.get('name', 'unnamed')}")
    
    def generate_from_rules(self, df: pd.DataFrame, 
                           value_cols: List[str],
                           timestamp_col: Optional[str] = None) -> pd.DataFrame:
        """
        基于规则生成标签
        
        Args:
            df: 输入 DataFrame
            value_cols: 用于判断的列
            timestamp_col: 时间戳列名
        
        Returns:
            包含标签列的 DataFrame
        """
        df_labeled = df.copy()
        
        # 初始化标签列
        df_labeled['label'] = 'normal'  # 默认正常
        df_labeled['label_code'] = 0
        df_labeled['label_reason'] = ''
        
        # 应用规则
        for i, rule in enumerate(self.rules):
            condition = rule.get('condition')
            label = rule.get('label', f'anomaly_{i}')
            label_code = rule.get('label_code', i + 1)
            reason = rule.get('reason', rule.get('name', ''))
            
            try:
                mask = self._evaluate_condition(df_labeled, condition, value_cols)
                
                if mask.any():
                    df_labeled.loc[mask, 'label'] = label
                    df_labeled.loc[mask, 'label_code'] = label_code
                    df_labeled.loc[mask, 'label_reason'] = reason
                    
                    logger.debug(f"规则 '{rule.get('name', i)}': {mask.sum()} 个样本标记为 {label}")
                    
            except Exception as e:
                logger.error(f"规则执行失败 {rule.get('name', i)}: {e}")
        
        # 保存标签映射
        unique_labels = df_labeled[['label', 'label_code', 'label_reason']].drop_duplicates()
        for _, row in unique_labels.iterrows():
            self.label_mapping[row['label_code']] = {
                'label': row['label'],
                'reason': row['label_reason']
            }
        
        logger.info(f"基于规则生成标签完成，总样本数：{len(df_labeled)}, 标签种类：{len(unique_labels)}")
        
        return df_labeled
    
    def _evaluate_condition(self, df: pd.DataFrame, 
                           condition: Dict[str, Any],
                           value_cols: List[str]) -> pd.Series:
        """评估条件"""
        cond_type = condition.get('type', 'threshold')
        
        if cond_type == 'threshold':
            # 阈值判断
            col = condition.get('column', value_cols[0])
            operator = condition.get('operator', '>')
            threshold = condition.get('threshold', 0)
            
            if operator == '>':
                return df[col] > threshold
            elif operator == '>=':
                return df[col] >= threshold
            elif operator == '<':
                return df[col] < threshold
            elif operator == '<=':
                return df[col] <= threshold
            elif operator == '==':
                return df[col] == threshold
            elif operator == '!=':
                return df[col] != threshold
            
        elif cond_type == 'range':
            # 范围判断
            col = condition.get('column', value_cols[0])
            min_val = condition.get('min', float('-inf'))
            max_val = condition.get('max', float('inf'))
            
            return (df[col] < min_val) | (df[col] > max_val)
        
        elif cond_type == 'rate_of_change':
            # 变化率判断
            col = condition.get('column', value_cols[0])
            window = condition.get('window', 5)
            threshold = condition.get('threshold', 0.1)
            
            rate = df[col].diff(window) / (df[col].shift(window) + 1e-8)
            return np.abs(rate) > threshold
        
        elif cond_type == 'duration':
            # 持续时间判断
            col = condition.get('column', value_cols[0])
            operator = condition.get('operator', '<')
            threshold = condition.get('threshold', 0)
            duration = condition.get('duration', 10)  # 时间步数
            
            # 基础条件
            if operator == '>':
                base_mask = df[col] > threshold
            elif operator == '<':
                base_mask = df[col] < threshold
            else:
                base_mask = df[col] == threshold
            
            # 检查持续时间
            result = pd.Series(False, index=df.index)
            consecutive_count = 0
            
            for idx in df.index:
                if base_mask[idx]:
                    consecutive_count += 1
                    if consecutive_count >= duration:
                        # 回溯标记
                        start_idx = df.index.get_loc(idx) - duration + 1
                        end_idx = df.index.get_loc(idx) + 1
                        result.iloc[start_idx:end_idx] = True
                else:
                    consecutive_count = 0
            
            return result
        
        elif cond_type == 'logic':
            # 逻辑组合
            logic_op = condition.get('logic', 'and')
            sub_conditions = condition.get('conditions', [])
            
            masks = [self._evaluate_condition(df, cond, value_cols) for cond in sub_conditions]
            
            if logic_op == 'and':
                result = masks[0]
                for mask in masks[1:]:
                    result = result & mask
                return result
            elif logic_op == 'or':
                result = masks[0]
                for mask in masks[1:]:
                    result = result | mask
                return result
        
        # 默认返回 False
        return pd.Series(False, index=df.index)
    
    def generate_from_clustering(self, df: pd.DataFrame,
                                 value_cols: List[str],
                                 method: str = 'dbscan',
                                 normalize: bool = True) -> pd.DataFrame:
        """
        基于聚类生成标签 (无监督)
        
        Args:
            df: 输入 DataFrame
            value_cols: 用于聚类的列
            method: 聚类方法 ('dbscan', 'kmeans')
            normalize: 是否标准化
        
        Returns:
            包含标签列的 DataFrame
        """
        df_clustered = df.copy()
        
        # 提取特征
        data = df_clustered[value_cols].values.astype(float)
        
        # 处理缺失值
        mask_valid = ~np.any(np.isnan(data), axis=1)
        data_valid = data[mask_valid]
        
        if len(data_valid) == 0:
            logger.warning("没有有效数据进行聚类")
            df_clustered['cluster_label'] = -1
            return df_clustered
        
        # 标准化
        if normalize:
            mean = data_valid.mean(axis=0)
            std = data_valid.std(axis=0)
            data_normalized = (data_valid - mean) / (std + 1e-8)
        else:
            data_normalized = data_valid
        
        # 聚类
        if method == 'dbscan':
            eps = self.config.get('dbscan_eps', 0.5)
            min_samples = self.config.get('dbscan_min_samples', 5)
            
            clusterer = DBSCAN(eps=eps, min_samples=min_samples)
            labels_valid = clusterer.fit_predict(data_normalized)
            
            logger.info(f"DBSCAN 聚类：{len(set(labels_valid))} 个簇，噪声点：{(labels_valid == -1).sum()}")
            
        elif method == 'kmeans':
            n_clusters = self.config.get('kmeans_n_clusters', 3)
            
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels_valid = clusterer.fit_predict(data_normalized)
            
            logger.info(f"KMeans 聚类：{n_clusters} 个簇")
        
        else:
            logger.error(f"不支持的聚类方法：{method}")
            df_clustered['cluster_label'] = -1
            return df_clustered
        
        # 将标签映射回原始数据
        df_clustered['cluster_label'] = -1
        df_clustered.loc[mask_valid, 'cluster_label'] = labels_valid
        
        # 转换为人可读的标签
        def cluster_to_label(code):
            if code == -1:
                return 'anomaly'
            else:
                return f'pattern_{code}'
        
        df_clustered['label'] = df_clustered['cluster_label'].apply(cluster_to_label)
        df_clustered['label_code'] = df_clustered['cluster_label']
        df_clustered['label_reason'] = '聚类自动发现的模式'
        
        # 更新标签映射
        for code in set(labels_valid):
            self.label_mapping[code] = {
                'label': cluster_to_label(code),
                'reason': f'聚类模式 {code}'
            }
        
        logger.info(f"基于聚类生成标签完成，样本数：{len(df_clustered)}")
        
        return df_clustered
    
    def generate_from_anomaly_score(self, df: pd.DataFrame,
                                   score_col: str,
                                   thresholds: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        基于异常分数生成标签
        
        Args:
            df: 输入 DataFrame
            score_col: 异常分数字段
            thresholds: 阈值配置 {'warning': 0.7, 'critical': 0.9}
        
        Returns:
            包含标签列的 DataFrame
        """
        df_labeled = df.copy()
        
        thresholds = thresholds or {
            'warning': self.config.get('warning_threshold', 0.7),
            'critical': self.config.get('critical_threshold', 0.9)
        }
        
        scores = df_labeled[score_col].values
        
        # 根据分数分配标签
        labels = []
        label_codes = []
        reasons = []
        
        for score in scores:
            if score >= thresholds['critical']:
                labels.append('critical')
                label_codes.append(3)
                reasons.append(f'异常分数 {score:.3f} >= {thresholds["critical"]}')
            elif score >= thresholds['warning']:
                labels.append('warning')
                label_codes.append(2)
                reasons.append(f'异常分数 {score:.3f} >= {thresholds["warning"]}')
            else:
                labels.append('normal')
                label_codes.append(0)
                reasons.append('')
        
        df_labeled['label'] = labels
        df_labeled['label_code'] = label_codes
        df_labeled['label_reason'] = reasons
        
        # 更新标签映射
        self.label_mapping[0] = {'label': 'normal', 'reason': '正常运行'}
        self.label_mapping[2] = {'label': 'warning', 'reason': '警告状态'}
        self.label_mapping[3] = {'label': 'critical', 'reason': '严重异常'}
        
        logger.info(f"基于异常分数生成标签：normal={labels.count('normal')}, "
                   f"warning={labels.count('warning')}, critical={labels.count('critical')}")
        
        return df_labeled
    
    def evaluate_labels(self, df: pd.DataFrame, label_col: str = 'label') -> Dict[str, Any]:
        """
        评估标签质量
        
        Args:
            df: 输入 DataFrame
            label_col: 标签列名
        
        Returns:
            评估指标
        """
        labels = df[label_col]
        
        # 基本统计
        label_counts = labels.value_counts()
        label_distribution = (label_counts / len(labels)).to_dict()
        
        # 不平衡度
        max_ratio = label_counts.max() / (label_counts.min() + 1e-8)
        
        # 标签熵 (衡量多样性)
        probs = label_counts.values / (label_counts.sum() + 1e-8)
        entropy = -np.sum(probs * np.log(probs + 1e-8))
        max_entropy = np.log(len(label_counts))
        normalized_entropy = entropy / (max_entropy + 1e-8)
        
        metrics = {
            'total_samples': len(labels),
            'num_labels': len(label_counts),
            'label_counts': label_counts.to_dict(),
            'label_distribution': label_distribution,
            'imbalance_ratio': max_ratio,
            'entropy': entropy,
            'normalized_entropy': normalized_entropy,
            'quality_score': normalized_entropy * (1 / (1 + np.log(max_ratio + 1)))
        }
        
        logger.info(f"标签质量评估：样本数={metrics['total_samples']}, "
                   f"标签数={metrics['num_labels']}, 质量分={metrics['quality_score']:.3f}")
        
        return metrics
    
    def export_mapping(self, path: str):
        """导出标签映射"""
        import json
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.label_mapping, f, ensure_ascii=False, indent=2)
        
        logger.info(f"标签映射已导出：{path}")
    
    def import_mapping(self, path: str):
        """导入标签映射"""
        import json
        
        with open(path, 'r', encoding='utf-8') as f:
            self.label_mapping = json.load(f)
        
        logger.info(f"标签映射已导入：{path}")


# 测试代码
if __name__ == "__main__":
    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='1min'),
        'temperature': 25 + np.random.randn(n_samples) * 2,
        'pressure': 1.0 + np.random.randn(n_samples) * 0.1,
        'flow_rate': 100 + np.random.randn(n_samples) * 5
    })
    
    # 注入一些异常
    df.loc[100:120, 'temperature'] = 40  # 温度突增
    df.loc[300:320, 'pressure'] = 0.5   # 压力下降
    df.loc[500:510, 'flow_rate'] = 200   # 流量激增
    
    print("测试数据:")
    print(df.head())
    print(f"形状：{df.shape}")
    
    # 初始化标签工厂
    factory = LabelFactory()
    
    # 添加规则
    factory.add_rule({
        'name': '高温异常',
        'condition': {
            'type': 'threshold',
            'column': 'temperature',
            'operator': '>',
            'threshold': 35
        },
        'label': 'high_temperature',
        'label_code': 1,
        'reason': '温度超过 35°C'
    })
    
    factory.add_rule({
        'name': '低压异常',
        'condition': {
            'type': 'threshold',
            'column': 'pressure',
            'operator': '<',
            'threshold': 0.7
        },
        'label': 'low_pressure',
        'label_code': 2,
        'reason': '压力低于 0.7MPa'
    })
    
    factory.add_rule({
        'name': '流量激增',
        'condition': {
            'type': 'threshold',
            'column': 'flow_rate',
            'operator': '>',
            'threshold': 150
        },
        'label': 'flow_spike',
        'label_code': 3,
        'reason': '流量超过 150L/min'
    })
    
    # 1. 基于规则生成标签
    print("\n=== 基于规则生成标签 ===")
    df_labeled = factory.generate_from_rules(df, ['temperature', 'pressure', 'flow_rate'])
    
    print(f"\n标签分布:")
    print(df_labeled['label'].value_counts())
    
    # 2. 基于聚类生成标签
    print("\n=== 基于聚类生成标签 ===")
    df_clustered = factory.generate_from_clustering(df, ['temperature', 'pressure', 'flow_rate'], method='dbscan')
    
    print(f"\n聚类标签分布:")
    print(df_clustered['label'].value_counts())
    
    # 3. 评估标签质量
    print("\n=== 标签质量评估 ===")
    metrics = factory.evaluate_labels(df_labeled, 'label')
    
    print(f"总样本数：{metrics['total_samples']}")
    print(f"标签种类：{metrics['num_labels']}")
    print(f"不平衡比：{metrics['imbalance_ratio']:.2f}")
    print(f"标签熵：{metrics['entropy']:.3f}")
    print(f"质量评分：{metrics['quality_score']:.3f}")
    
    # 4. 导出标签映射
    factory.export_mapping('test_label_mapping.json')
