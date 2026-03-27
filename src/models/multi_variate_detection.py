"""
多变量异常检测模块

功能需求: A-03 多变量检测 - 考虑变量间关系
作者: ML Team
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.covariance import EllipticEnvelope
from sklearn.neighbors import LocalOutlierFactor
from scipy import stats
from scipy.spatial.distance import mahalanobis
import warnings
warnings.filterwarnings('ignore')

from loguru import logger


class MultiVariateAnomalyDetector:
    """
    多变量异常检测器
    
    算法:
    1. 马氏距离 (Mahalanobis Distance)
    2. 孤立森林多变量版
    3. 局部异常因子 (LOF)
    4. 椭圆包络 (Elliptic Envelope)
    5. 主成分异常 (PCA-based)
    """
    
    def __init__(self, method: str = "mahalanobis", contamination: float = 0.1):
        """
        初始化检测器
        
        Args:
            method: 检测方法 (mahalanobis/isolation_forest/lof/elliptic_envelope/pca)
            contamination: 预期异常比例
        """
        self.method = method
        self.contamination = contamination
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # 马氏距离专用
        self.cov_matrix = None
        self.cov_inv = None
        self.mean_vector = None
        
        logger.info(f"多变量异常检测器初始化: method={method}")
    
    def fit(self, df: pd.DataFrame, feature_cols: List[str]):
        """
        训练模型
        
        Args:
            df: 训练数据
            feature_cols: 特征列名列表
        """
        X = df[feature_cols].values
        X_scaled = self.scaler.fit_transform(X)
        
        if self.method == "mahalanobis":
            self._fit_mahalanobis(X_scaled)
        elif self.method == "isolation_forest":
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            self.model.fit(X_scaled)
        elif self.method == "lof":
            self.model = LocalOutlierFactor(
                n_neighbors=20,
                contamination=self.contamination,
                novelty=True
            )
            self.model.fit(X_scaled)
        elif self.method == "elliptic_envelope":
            self.model = EllipticEnvelope(
                contamination=self.contamination,
                random_state=42
            )
            self.model.fit(X_scaled)
        elif self.method == "pca":
            self._fit_pca(X_scaled)
        
        self.is_fitted = True
        self.feature_cols = feature_cols
        
        logger.info(f"模型训练完成: {len(df)} 样本, {len(feature_cols)} 特征")
    
    def _fit_mahalanobis(self, X: np.ndarray):
        """拟合马氏距离参数"""
        self.mean_vector = np.mean(X, axis=0)
        self.cov_matrix = np.cov(X, rowvar=False)
        
        # 添加正则化防止奇异矩阵
        self.cov_matrix += np.eye(self.cov_matrix.shape[0]) * 1e-6
        self.cov_inv = np.linalg.inv(self.cov_matrix)
    
    def _fit_pca(self, X: np.ndarray, n_components: float = 0.95):
        """拟合PCA模型"""
        self.pca = PCA(n_components=n_components)
        self.pca.fit(X)
        
        # 计算训练数据的重构误差阈值
        X_reconstructed = self.pca.inverse_transform(self.pca.transform(X))
        reconstruction_errors = np.sum((X - X_reconstructed) ** 2, axis=1)
        
        # 设置阈值 (使用3-sigma原则)
        self.pca_threshold = np.mean(reconstruction_errors) + 3 * np.std(reconstruction_errors)
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        预测异常
        
        Args:
            df: 待检测数据
            
        Returns:
            异常标签 (-1: 异常, 1: 正常)
        """
        if not self.is_fitted:
            raise ValueError("模型未训练")
        
        X = df[self.feature_cols].values
        X_scaled = self.scaler.transform(X)
        
        if self.method == "mahalanobis":
            scores = self._mahalanobis_distance(X_scaled)
            threshold = stats.chi2.ppf(0.975, df=len(self.feature_cols))
            return np.where(scores > threshold, -1, 1)
        elif self.method == "pca":
            errors = self._pca_reconstruction_error(X_scaled)
            return np.where(errors > self.pca_threshold, -1, 1)
        else:
            return self.model.predict(X_scaled)
    
    def score(self, df: pd.DataFrame) -> np.ndarray:
        """
        获取异常分数
        
        Args:
            df: 待检测数据
            
        Returns:
            异常分数 (越大越异常)
        """
        if not self.is_fitted:
            raise ValueError("模型未训练")
        
        X = df[self.feature_cols].values
        X_scaled = self.scaler.transform(X)
        
        if self.method == "mahalanobis":
            return self._mahalanobis_distance(X_scaled)
        elif self.method == "pca":
            return self._pca_reconstruction_error(X_scaled)
        elif self.method == "isolation_forest":
            return -self.model.score_samples(X_scaled)  # 转为正数，越大越异常
        else:
            # 其他方法返回异常概率
            return -self.model.score_samples(X_scaled)
    
    def _mahalanobis_distance(self, X: np.ndarray) -> np.ndarray:
        """计算马氏距离"""
        distances = []
        for x in X:
            diff = x - self.mean_vector
            dist = np.sqrt(diff @ self.cov_inv @ diff)
            distances.append(dist)
        return np.array(distances)
    
    def _pca_reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        """计算PCA重构误差"""
        X_transformed = self.pca.transform(X)
        X_reconstructed = self.pca.inverse_transform(X_transformed)
        errors = np.sum((X - X_reconstructed) ** 2, axis=1)
        return errors
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        完整检测流程
        
        Args:
            df: 待检测数据
            
        Returns:
            添加异常标记的数据框
        """
        result_df = df.copy()
        
        # 预测标签
        labels = self.predict(df)
        result_df['is_anomaly'] = labels == -1
        
        # 异常分数
        scores = self.score(df)
        result_df['anomaly_score'] = scores
        
        # 各变量贡献度 (仅PCA方法)
        if self.method == "pca":
            contributions = self._calculate_contributions(df)
            for col, contrib in contributions.items():
                result_df[f'{col}_contribution'] = contrib
        
        return result_df
    
    def _calculate_contributions(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """计算各变量对异常的贡献度"""
        X = df[self.feature_cols].values
        X_scaled = self.scaler.transform(X)
        
        X_transformed = self.pca.transform(X_scaled)
        X_reconstructed = self.pca.inverse_transform(X_transformed)
        
        # 计算每个变量的重构误差
        errors = (X_scaled - X_reconstructed) ** 2
        
        contributions = {}
        for i, col in enumerate(self.feature_cols):
            contributions[col] = errors[:, i]
        
        return contributions
    
    def get_correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """获取变量相关性矩阵"""
        return df[self.feature_cols].corr()
    
    def explain_anomaly(self, record: pd.Series) -> Dict[str, float]:
        """
        解释异常原因
        
        Args:
            record: 单条记录
            
        Returns:
            各变量异常贡献度
        """
        if not self.is_fitted:
            raise ValueError("模型未训练")
        
        # 计算与均值的偏差
        X = record[self.feature_cols].values.reshape(1, -1)
        X_scaled = self.scaler.transform(X)[0]
        
        # 使用马氏距离分量解释
        if self.method == "mahalanobis":
            diff = X_scaled - self.mean_vector
            contributions = diff ** 2 * np.diag(self.cov_inv)
        else:
            # 使用标准化后的绝对值
            contributions = np.abs(X_scaled)
        
        # 归一化为百分比
        total = np.sum(contributions)
        if total > 0:
            contributions = contributions / total * 100
        
        return {col: contrib for col, contrib in zip(self.feature_cols, contributions)}


class CorrelationAnomalyDetector:
    """
    相关性异常检测器
    
    检测变量间相关性的变化
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.baseline_corr = None
        self.feature_cols = None
    
    def fit(self, df: pd.DataFrame, feature_cols: List[str]):
        """建立相关性基线"""
        self.feature_cols = feature_cols
        self.baseline_corr = df[feature_cols].corr().values
        logger.info("相关性基线已建立")
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """检测相关性异常"""
        result_df = df.copy()
        
        # 滑动窗口计算相关性
        anomalies = []
        for i in range(len(df)):
            if i < self.window_size:
                anomalies.append(False)
                continue
            
            window = df.iloc[i-self.window_size:i][self.feature_cols]
            current_corr = window.corr().values
            
            # 计算相关性差异
            corr_diff = np.abs(current_corr - self.baseline_corr)
            max_diff = np.max(corr_diff)
            
            # 阈值判断
            anomalies.append(max_diff > 0.5)
        
        result_df['correlation_anomaly'] = anomalies
        return result_df


# 使用示例
if __name__ == "__main__":
    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    
    # 正常数据：相关变量
    x1 = np.random.normal(10, 2, n_samples)
    x2 = x1 * 0.8 + np.random.normal(0, 1, n_samples)  # 与x1相关
    x3 = np.random.normal(5, 1, n_samples)  # 独立
    
    # 添加异常
    x1[950:960] = 20  # 异常值
    x2[950:960] = 5   # 违反相关性
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='min'),
        'temperature': x1,
        'pressure': x2,
        'flow': x3
    })
    
    feature_cols = ['temperature', 'pressure', 'flow']
    
    # 测试不同方法
    for method in ['mahalanobis', 'isolation_forest', 'pca']:
        print(f"\n{'='*50}")
        print(f"方法: {method}")
        print('='*50)
        
        detector = MultiVariateAnomalyDetector(method=method)
        
        # 训练
        train_df = df.iloc[:800]
        detector.fit(train_df, feature_cols)
        
        # 检测
        test_df = df.iloc[800:]
        result = detector.detect(test_df)
        
        # 统计
        n_anomalies = result['is_anomaly'].sum()
        print(f"检测到异常: {n_anomalies} 条")
        
        # 显示异常样本
        anomalies = result[result['is_anomaly']].head(3)
        if not anomalies.empty:
            print("\n异常样本:")
            print(anomalies[feature_cols + ['anomaly_score']])
        
        # 解释异常
        if n_anomalies > 0:
            sample_anomaly = result[result['is_anomaly']].iloc[0]
            explanation = detector.explain_anomaly(sample_anomaly)
            print("\n异常原因分析:")
            for var, contrib in explanation.items():
                print(f"  {var}: {contrib:.1f}%")
