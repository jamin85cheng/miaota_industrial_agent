"""
自适应阈值模块

功能需求: A-04 自适应阈值 - 根据历史数据自动调整
作者: ML Team
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque
from scipy import stats
from scipy.ndimage import gaussian_filter1d
import warnings
warnings.filterwarnings('ignore')

from loguru import logger


@dataclass
class ThresholdConfig:
    """阈值配置"""
    upper_percentile: float = 95.0  # 上边界百分位
    lower_percentile: float = 5.0   # 下边界百分位
    min_window_size: int = 100      # 最小窗口大小
    max_window_size: int = 10000    # 最大窗口大小
    adaptation_rate: float = 0.1    # 自适应速率
    seasonality_period: Optional[int] = None  # 周期性 (小时)
    smooth_sigma: float = 2.0       # 平滑系数


class AdaptiveThreshold:
    """
    自适应阈值检测器
    
    特点:
    1. 动态调整阈值边界
    2. 支持周期性数据
    3. 平滑处理减少噪声
    4. 多策略融合
    """
    
    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()
        self.history: deque = deque(maxlen=self.config.max_window_size)
        self.current_thresholds: Dict[str, Tuple[float, float]] = {}
        self.is_fitted = False
        
        # 季节性调整
        self.seasonal_baselines: Dict[int, Dict] = {}
        
        logger.info("自适应阈值检测器已初始化")
    
    def fit(self, data: pd.Series, timestamp_col: Optional[pd.Series] = None):
        """
        训练自适应阈值
        
        Args:
            data: 历史数据
            timestamp_col: 时间戳列 (用于季节性调整)
        """
        values = data.values if isinstance(data, pd.Series) else np.array(data)
        
        # 存储历史
        self.history.extend(values)
        
        # 计算基础阈值
        self._update_thresholds()
        
        # 如果有时间戳，计算季节性基线
        if timestamp_col is not None and self.config.seasonality_period:
            self._calculate_seasonal_baselines(values, timestamp_col)
        
        self.is_fitted = True
        
        logger.info(f"自适应阈值训练完成: {len(values)} 样本")
    
    def _update_thresholds(self):
        """更新阈值"""
        if len(self.history) < self.config.min_window_size:
            return
        
        data = np.array(self.history)
        
        # 平滑处理
        if len(data) > 10:
            smoothed = gaussian_filter1d(data, sigma=self.config.smooth_sigma)
        else:
            smoothed = data
        
        # 计算百分位数
        upper = np.percentile(smoothed, self.config.upper_percentile)
        lower = np.percentile(smoothed, self.config.lower_percentile)
        
        # 使用3-sigma作为备用边界
        mean = np.mean(smoothed)
        std = np.std(smoothed)
        upper_3sigma = mean + 3 * std
        lower_3sigma = mean - 3 * std
        
        # 取更严格的边界
        upper_bound = min(upper, upper_3sigma)
        lower_bound = max(lower, lower_3sigma)
        
        self.current_thresholds = {
            'upper': upper_bound,
            'lower': lower_bound,
            'mean': mean,
            'std': std
        }
    
    def _calculate_seasonal_baselines(self, values: np.ndarray, timestamps: pd.Series):
        """计算季节性基线"""
        df = pd.DataFrame({
            'timestamp': timestamps,
            'value': values
        })
        df['hour'] = df['timestamp'].dt.hour
        
        # 按小时计算统计
        hourly_stats = df.groupby('hour')['value'].agg(['mean', 'std', 'quantile'])
        
        for hour in range(24):
            if hour in hourly_stats.index:
                stats = hourly_stats.loc[hour]
                self.seasonal_baselines[hour] = {
                    'mean': stats['mean'],
                    'std': stats['std'],
                    'upper': stats['mean'] + 2 * stats['std'],
                    'lower': stats['mean'] - 2 * stats['std']
                }
        
        logger.info("季节性基线计算完成")
    
    def predict(self, value: float, timestamp: Optional[datetime] = None) -> Dict:
        """
        预测是否为异常
        
        Args:
            value: 待检测值
            timestamp: 时间戳 (用于季节性调整)
            
        Returns:
            检测结果字典
        """
        if not self.is_fitted:
            raise ValueError("模型未训练")
        
        # 获取当前阈值
        thresholds = self._get_thresholds_for_timestamp(timestamp)
        
        # 检测
        is_anomaly = value > thresholds['upper'] or value < thresholds['lower']
        
        # 计算异常程度
        if value > thresholds['upper']:
            severity = (value - thresholds['upper']) / thresholds['std'] if thresholds['std'] > 0 else 0
            direction = 'high'
        elif value < thresholds['lower']:
            severity = (thresholds['lower'] - value) / thresholds['std'] if thresholds['std'] > 0 else 0
            direction = 'low'
        else:
            severity = 0
            direction = 'normal'
        
        return {
            'is_anomaly': is_anomaly,
            'direction': direction,
            'severity': severity,
            'value': value,
            'thresholds': thresholds
        }
    
    def _get_thresholds_for_timestamp(self, timestamp: Optional[datetime]) -> Dict:
        """获取指定时间的阈值"""
        base_thresholds = self.current_thresholds.copy()
        
        # 季节性调整
        if timestamp and self.config.seasonality_period and self.seasonal_baselines:
            hour = timestamp.hour
            if hour in self.seasonal_baselines:
                seasonal = self.seasonal_baselines[hour]
                # 融合基础阈值和季节性阈值
                alpha = self.config.adaptation_rate
                base_thresholds['upper'] = (1 - alpha) * base_thresholds['upper'] + alpha * seasonal['upper']
                base_thresholds['lower'] = (1 - alpha) * base_thresholds['lower'] + alpha * seasonal['lower']
        
        return base_thresholds
    
    def update(self, value: float):
        """
        在线更新阈值
        
        Args:
            value: 新观测值
        """
        self.history.append(value)
        
        # 定期更新阈值
        if len(self.history) % 100 == 0:
            self._update_thresholds()
    
    def get_threshold_history(self, n_points: int = 100) -> pd.DataFrame:
        """获取阈值历史变化"""
        # 简化实现，实际应记录历史阈值
        data = list(self.history)[-n_points:]
        
        return pd.DataFrame({
            'value': data,
            'upper_threshold': [self.current_thresholds.get('upper', np.nan)] * len(data),
            'lower_threshold': [self.current_thresholds.get('lower', np.nan)] * len(data)
        })


class DynamicThresholdManager:
    """
    动态阈值管理器
    
    管理多个点位的自适应阈值
    """
    
    def __init__(self):
        self.detectors: Dict[str, AdaptiveThreshold] = {}
    
    def fit(self, tag_id: str, data: pd.Series, 
            timestamp_col: Optional[pd.Series] = None,
            config: Optional[ThresholdConfig] = None):
        """为指定点位训练阈值"""
        detector = AdaptiveThreshold(config)
        detector.fit(data, timestamp_col)
        self.detectors[tag_id] = detector
        
        logger.info(f"点位 {tag_id} 的自适应阈值已训练")
    
    def detect(self, tag_id: str, value: float, 
               timestamp: Optional[datetime] = None) -> Dict:
        """检测指定点位"""
        if tag_id not in self.detectors:
            raise ValueError(f"点位 {tag_id} 未训练")
        
        return self.detectors[tag_id].predict(value, timestamp)
    
    def update(self, tag_id: str, value: float):
        """更新指定点位"""
        if tag_id in self.detectors:
            self.detectors[tag_id].update(value)
    
    def get_all_thresholds(self) -> Dict[str, Dict]:
        """获取所有点位的当前阈值"""
        return {
            tag_id: detector.current_thresholds
            for tag_id, detector in self.detectors.items()
        }


# 使用示例
if __name__ == "__main__":
    # 生成测试数据 (带趋势和周期性)
    np.random.seed(42)
    n_samples = 2000
    
    # 基础值 + 趋势 + 周期性 + 噪声
    t = np.arange(n_samples)
    trend = 0.001 * t
    seasonal = 2 * np.sin(2 * np.pi * t / 288)  # 24小时周期 (每5分钟一个点)
    noise = np.random.normal(0, 0.5, n_samples)
    
    values = 10 + trend + seasonal + noise
    
    # 添加异常
    values[1500:1510] = 20  # 高点异常
    values[1600:1610] = 2   # 低点异常
    
    timestamps = pd.date_range('2024-01-01', periods=n_samples, freq='5min')
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    # 训练自适应阈值
    config = ThresholdConfig(
        upper_percentile=97.5,
        lower_percentile=2.5,
        seasonality_period=24,
        adaptation_rate=0.2
    )
    
    detector = AdaptiveThreshold(config)
    
    # 使用前1500条训练
    train_df = df.iloc[:1500]
    detector.fit(train_df['value'], train_df['timestamp'])
    
    print("训练完成，当前阈值:")
    print(f"  上边界: {detector.current_thresholds['upper']:.2f}")
    print(f"  下边界: {detector.current_thresholds['lower']:.2f}")
    print(f"  均值: {detector.current_thresholds['mean']:.2f}")
    print(f"  标准差: {detector.current_thresholds['std']:.2f}")
    
    # 检测异常
    print("\n检测异常 (最后500条):")
    test_df = df.iloc[1500:]
    anomalies = []
    
    for idx, row in test_df.iterrows():
        result = detector.predict(row['value'], row['timestamp'])
        detector.update(row['value'])
        
        if result['is_anomaly']:
            anomalies.append({
                'timestamp': row['timestamp'],
                'value': row['value'],
                'direction': result['direction'],
                'severity': result['severity']
            })
    
    print(f"共检测到 {len(anomalies)} 个异常")
    
    # 显示前几个异常
    for a in anomalies[:5]:
        print(f"  {a['timestamp']}: {a['value']:.2f} ({a['direction']}, severity={a['severity']:.2f})")
