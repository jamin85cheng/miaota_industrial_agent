"""
数据预处理模块

功能：
- 数据清洗 (缺失值、异常值处理)
- 特征工程 (统计特征、时域特征、频域特征)
- 数据标准化/归一化
- 滑动窗口处理
- 数据对齐与重采样
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from scipy import stats
from scipy.signal import butter, filtfilt, fft
from loguru import logger


class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.scalers = {}  # 保存标准化器
        self.feature_names = []  # 特征名称
    
    def clean(self, df: pd.DataFrame, method: str = "interpolate",
              outlier_method: str = "iqr", 
              outlier_threshold: float = 1.5) -> pd.DataFrame:
        """
        数据清洗
        
        Args:
            df: 输入 DataFrame
            method: 缺失值处理方法 ("drop", "fill_zero", "fill_mean", "interpolate", "forward_fill")
            outlier_method: 异常值处理方法 ("iqr", "zscore", "clip")
            outlier_threshold: 异常值阈值
        
        Returns:
            清洗后的 DataFrame
        """
        df_clean = df.copy()
        
        # 1. 处理缺失值
        if method == "drop":
            df_clean = df_clean.dropna()
        elif method == "fill_zero":
            df_clean = df_clean.fillna(0)
        elif method == "fill_mean":
            df_clean = df_clean.fillna(df_clean.mean())
        elif method == "interpolate":
            df_clean = df_clean.interpolate(method='linear')
        elif method == "forward_fill":
            df_clean = df_clean.fillna(method='ffill')
        
        logger.debug(f"缺失值处理：{method}, 剩余缺失值：{df_clean.isnull().sum().sum()}")
        
        # 2. 处理异常值
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if outlier_method == "iqr":
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - outlier_threshold * IQR
                upper = Q3 + outlier_threshold * IQR
                df_clean[col] = df_clean[col].clip(lower, upper)
                
            elif outlier_method == "zscore":
                z_scores = np.abs(stats.zscore(df_clean[col].dropna()))
                mask = z_scores > outlier_threshold
                if mask.any():
                    median = df_clean[col].median()
                    df_clean.loc[mask.index[mask], col] = median
            
            elif outlier_method == "clip":
                lower = df_clean[col].quantile(outlier_threshold / 100)
                upper = df_clean[col].quantile(1 - outlier_threshold / 100)
                df_clean[col] = df_clean[col].clip(lower, upper)
        
        logger.debug(f"异常值处理：{outlier_method}")
        
        return df_clean
    
    def normalize(self, df: pd.DataFrame, method: str = "zscore",
                  columns: Optional[List[str]] = None,
                  fit: bool = True) -> pd.DataFrame:
        """
        数据标准化/归一化
        
        Args:
            df: 输入 DataFrame
            method: 方法 ("zscore", "minmax", "robust")
            columns: 要处理的列，None 表示所有数值列
            fit: 是否拟合并保存参数 (用于后续转换)
        
        Returns:
            标准化后的 DataFrame
        """
        df_norm = df.copy()
        
        if columns is None:
            columns = df_norm.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if method == "zscore":
                if fit:
                    mean = df_norm[col].mean()
                    std = df_norm[col].std()
                    self.scalers[f"{col}_mean"] = mean
                    self.scalers[f"{col}_std"] = std
                else:
                    mean = self.scalers.get(f"{col}_mean", df_norm[col].mean())
                    std = self.scalers.get(f"{col}_std", df_norm[col].std())
                
                df_norm[col] = (df_norm[col] - mean) / (std + 1e-8)
                
            elif method == "minmax":
                if fit:
                    min_val = df_norm[col].min()
                    max_val = df_norm[col].max()
                    self.scalers[f"{col}_min"] = min_val
                    self.scalers[f"{col}_max"] = max_val
                else:
                    min_val = self.scalers.get(f"{col}_min", df_norm[col].min())
                    max_val = self.scalers.get(f"{col}_max", df_norm[col].max())
                
                range_val = max_val - min_val
                df_norm[col] = (df_norm[col] - min_val) / (range_val + 1e-8)
                
            elif method == "robust":
                if fit:
                    median = df_norm[col].median()
                    q1 = df_norm[col].quantile(0.25)
                    q3 = df_norm[col].quantile(0.75)
                    self.scalers[f"{col}_median"] = median
                    self.scalers[f"{col}_iqr"] = q3 - q1
                else:
                    median = self.scalers.get(f"{col}_median", df_norm[col].median())
                    iqr = self.scalers.get(f"{col}_iqr", df_norm[col].quantile(0.75) - df_norm[col].quantile(0.25))
                
                df_norm[col] = (df_norm[col] - median) / (iqr + 1e-8)
        
        logger.debug(f"数据标准化：{method}, 列数：{len(columns)}")
        return df_norm
    
    def extract_features(self, df: pd.DataFrame, 
                        value_cols: Optional[List[str]] = None,
                        window_size: int = 10,
                        include_freq: bool = False) -> pd.DataFrame:
        """
        特征工程 - 提取统计特征和时域特征
        
        Args:
            df: 输入 DataFrame (索引应为时间序列)
            value_cols: 要提取特征的列，None 表示所有数值列
            window_size: 滑动窗口大小
            include_freq: 是否包含频域特征
        
        Returns:
            包含原始特征和衍生特征的 DataFrame
        """
        df_features = df.copy()
        
        if value_cols is None:
            value_cols = df_features.select_dtypes(include=[np.number]).columns.tolist()
        
        new_features = []
        
        for col in value_cols:
            # 1. 基础统计特征
            df_features[f"{col}_rolling_mean_{window_size}"] = df_features[col].rolling(window=window_size).mean()
            df_features[f"{col}_rolling_std_{window_size}"] = df_features[col].rolling(window=window_size).std()
            df_features[f"{col}_rolling_min_{window_size}"] = df_features[col].rolling(window=window_size).min()
            df_features[f"{col}_rolling_max_{window_size}"] = df_features[col].rolling(window=window_size).max()
            
            # 2. 变化率特征
            df_features[f"{col}_diff_1"] = df_features[col].diff(1)  # 一阶差分
            df_features[f"{col}_diff_2"] = df_features[col].diff(2)  # 二阶差分
            df_features[f"{col}_pct_change"] = df_features[col].pct_change()  # 百分比变化
            
            # 3. 滞后特征
            for lag in [1, 2, 3]:
                df_features[f"{col}_lag_{lag}"] = df_features[col].shift(lag)
            
            # 4. 指数加权移动平均
            df_features[f"{col}_ewm_10"] = df_features[col].ewm(span=10).mean()
            df_features[f"{col}_ewm_50"] = df_features[col].ewm(span=50).mean()
            
            new_features.extend([
                f"{col}_rolling_mean_{window_size}",
                f"{col}_rolling_std_{window_size}",
                f"{col}_rolling_min_{window_size}",
                f"{col}_rolling_max_{window_size}",
                f"{col}_diff_1",
                f"{col}_diff_2",
                f"{col}_pct_change",
                f"{col}_lag_1",
                f"{col}_lag_2",
                f"{col}_lag_3",
                f"{col}_ewm_10",
                f"{col}_ewm_50"
            ])
            
            # 5. 频域特征 (可选)
            if include_freq:
                try:
                    freq_features = self._extract_frequency_features(df_features[col].values, window_size)
                    for i, feat in enumerate(freq_features):
                        feat_name = f"{col}_freq_{i}"
                        df_features[feat_name] = feat
                        new_features.append(feat_name)
                except Exception as e:
                    logger.warning(f"提取频域特征失败 ({col}): {e}")
        
        # 移除包含 NaN 的行 (由 rolling/diff 等操作产生)
        df_features = df_features.dropna()
        
        self.feature_names = list(value_cols) + new_features
        logger.info(f"特征工程完成：原始 {len(value_cols)} 列 → {len(self.feature_names)} 列")
        
        return df_features
    
    def _extract_frequency_features(self, signal: np.ndarray, window_size: int) -> List[np.ndarray]:
        """提取频域特征"""
        n = len(signal)
        if n < window_size:
            return []
        
        # FFT 变换
        fft_vals = np.fft.fft(signal[-window_size:])
        fft_freq = np.fft.fftfreq(window_size)
        
        # 主要频率成分
        magnitude = np.abs(fft_vals[:window_size // 2])
        dominant_freq = fft_freq[np.argmax(magnitude)]
        total_energy = np.sum(magnitude ** 2)
        spectral_entropy = -np.sum(magnitude * np.log(magnitude + 1e-10))
        
        # 频段能量
        freq_bands = {
            'low': (0, 0.1),
            'mid': (0.1, 0.3),
            'high': (0.3, 0.5)
        }
        
        features = []
        features.append(np.full(n, dominant_freq))  # 主频
        features.append(np.full(n, total_energy))  # 总能量
        features.append(np.full(n, spectral_entropy))  # 频谱熵
        
        for band_name, (low, high) in freq_bands.items():
            mask = (np.abs(fft_freq[:window_size // 2]) >= low) & (np.abs(fft_freq[:window_size // 2]) < high)
            band_energy = np.sum(magnitude[mask] ** 2)
            features.append(np.full(n, band_energy))
        
        return features
    
    def resample(self, df: pd.DataFrame, rule: str = '1T', 
                 method: str = 'mean', fill_na: str = 'interpolate') -> pd.DataFrame:
        """
        数据重采样
        
        Args:
            df: 输入 DataFrame (索引应为 DatetimeIndex)
            rule: 重采样频率 ('1T'=1 分钟，'5T'=5 分钟，'1H'=1 小时)
            method: 聚合方法 ('mean', 'sum', 'max', 'min', 'first', 'last')
            fill_na: 填充方法 ('interpolate', 'forward_fill', 'none')
        
        Returns:
            重采样后的 DataFrame
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("索引不是 DatetimeIndex，尝试转换...")
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                logger.error(f"无法转换为时间索引：{e}")
                return df
        
        # 重采样
        if method == 'mean':
            df_resampled = df.resample(rule).mean()
        elif method == 'sum':
            df_resampled = df.resample(rule).sum()
        elif method == 'max':
            df_resampled = df.resample(rule).max()
        elif method == 'min':
            df_resampled = df.resample(rule).min()
        elif method == 'first':
            df_resampled = df.resample(rule).first()
        elif method == 'last':
            df_resampled = df.resample(rule).last()
        else:
            df_resampled = df.resample(rule).mean()
        
        # 填充缺失值
        if fill_na == 'interpolate':
            df_resampled = df_resampled.interpolate(method='linear')
        elif fill_na == 'forward_fill':
            df_resampled = df_resampled.fillna(method='ffill')
        
        logger.info(f"数据重采样：{rule}, 方法：{method}, 原始 {len(df)} 行 → {len(df_resampled)} 行")
        return df_resampled
    
    def align(self, df: pd.DataFrame, target_cols: List[str],
              method: str = 'nearest', tolerance: Optional[str] = None) -> pd.DataFrame:
        """
        多传感器数据对齐
        
        Args:
            df: 输入 DataFrame
            target_cols: 要对齐的列
            method: 对齐方法 ('nearest', 'forward', 'backward')
            tolerance: 时间容差 (如 '1s', '1min')
        
        Returns:
            对齐后的 DataFrame
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # 创建基准时间序列 (使用第一列的时间戳)
        base_col = target_cols[0]
        base_times = df[df[base_col].notna()].index
        
        # 对其他列进行对齐
        aligned_df = pd.DataFrame(index=base_times)
        aligned_df[base_col] = df.loc[base_times, base_col]
        
        for col in target_cols[1:]:
            if method == 'nearest':
                aligned_df[col] = df[col].reindex(base_times, method='nearest', tolerance=tolerance)
            elif method == 'forward':
                aligned_df[col] = df[col].reindex(base_times, method='ffill', tolerance=tolerance)
            elif method == 'backward':
                aligned_df[col] = df[col].reindex(base_times, method='bfill', tolerance=tolerance)
        
        logger.info(f"数据对齐：{len(target_cols)} 列，方法：{method}")
        return aligned_df
    
    def create_sliding_windows(self, df: pd.DataFrame, 
                               window_size: int = 60,
                               stride: int = 1,
                               include_target: bool = True,
                               target_col: Optional[str] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        创建滑动窗口 (用于时序预测/分类)
        
        Args:
            df: 输入 DataFrame
            window_size: 窗口大小
            stride: 步长
            include_target: 是否包含目标变量
            target_col: 目标变量列名
        
        Returns:
            (X, y) 元组，X 为特征窗口，y 为目标值 (如果 include_target=True)
        """
        data = df.values
        
        X = []
        y = []
        
        for i in range(0, len(data) - window_size, stride):
            window = data[i:i + window_size]
            X.append(window)
            
            if include_target and target_col:
                target_idx = df.columns.get_loc(target_col)
                # 预测下一个时间点
                y.append(data[i + window_size, target_idx])
        
        X = np.array(X)
        y = np.array(y) if include_target else None
        
        logger.info(f"创建滑动窗口：窗口大小={window_size}, 步长={stride}, 样本数={len(X)}")
        return X, y


# 测试代码
if __name__ == "__main__":
    # 生成测试数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='1min')
    df = pd.DataFrame({
        'temperature': 25 + np.random.randn(1000) * 2,
        'pressure': 1.0 + np.random.randn(1000) * 0.1,
        'flow_rate': 100 + np.random.randn(1000) * 5
    }, index=dates)
    
    # 添加一些缺失值和异常值
    df.loc[df.sample(50).index, 'temperature'] = np.nan
    df.loc[df.sample(10).index, 'pressure'] = df.loc[df.sample(10).index, 'pressure'] * 10
    
    print("原始数据:")
    print(df.head())
    print(f"形状：{df.shape}")
    
    # 初始化预处理器
    preprocessor = DataPreprocessor()
    
    # 1. 数据清洗
    df_clean = preprocessor.clean(df, method='interpolate', outlier_method='iqr')
    print("\n清洗后数据:")
    print(df_clean.head())
    
    # 2. 特征工程
    df_features = preprocessor.extract_features(df_clean, window_size=10)
    print(f"\n特征工程后形状：{df_features.shape}")
    print(f"特征数量：{len(preprocessor.feature_names)}")
    
    # 3. 标准化
    df_norm = preprocessor.normalize(df_features, method='zscore')
    print("\n标准化后统计:")
    print(df_norm.describe())
    
    # 4. 重采样
    df_resampled = preprocessor.resample(df_clean, rule='5T', method='mean')
    print(f"\n重采样后形状：{df_resampled.shape}")
    
    # 5. 滑动窗口
    X, y = preprocessor.create_sliding_windows(df_norm, window_size=10, target_col='temperature')
    print(f"\n滑动窗口：X={X.shape}, y={y.shape}")
