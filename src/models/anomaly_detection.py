"""
异常检测模块
支持 Isolation Forest、LSTM Autoencoder 等算法
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from pathlib import Path
import pickle

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, method: str = 'isolation_forest', config: Optional[Dict[str, Any]] = None):
        """
        初始化异常检测器
        
        Args:
            method: 检测方法 ('isolation_forest', 'lstm_ae', 'dbscan')
            config: 算法配置参数
        """
        self.method = method
        self.config = config or {}
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        logger.info(f"AnomalyDetector 初始化完成：method={method}")
    
    def fit(self, data: pd.DataFrame, **kwargs):
        """
        训练模型
        
        Args:
            data: 训练数据 (正常工况数据)
        """
        logger.info(f"开始训练异常检测模型：{self.method}")
        
        # 数据预处理
        X = self._preprocess(data)
        
        if self.method == 'isolation_forest':
            self._fit_isolation_forest(X, **kwargs)
        elif self.method == 'dbscan':
            self._fit_dbscan(X, **kwargs)
        else:
            raise ValueError(f"不支持的检测方法：{self.method}")
        
        self.is_fitted = True
        logger.info("模型训练完成")
    
    def _preprocess(self, data: pd.DataFrame) -> np.ndarray:
        """数据预处理"""
        # 去除空值
        X = data.dropna().values
        
        # 标准化
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled
    
    def _fit_isolation_forest(self, X: np.ndarray, **kwargs):
        """训练 Isolation Forest"""
        contamination = kwargs.get('contamination', self.config.get('contamination', 0.05))
        n_estimators = kwargs.get('n_estimators', self.config.get('n_estimators', 100))
        random_state = kwargs.get('random_state', 42)
        
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            **kwargs
        )
        self.model.fit(X)
        logger.info(f"Isolation Forest 训练完成 (n_estimators={n_estimators})")
    
    def _fit_dbscan(self, X: np.ndarray, **kwargs):
        """训练 DBSCAN"""
        from sklearn.cluster import DBSCAN
        
        eps = kwargs.get('eps', self.config.get('eps', 0.5))
        min_samples = kwargs.get('min_samples', self.config.get('min_samples', 5))
        
        self.model = DBSCAN(eps=eps, min_samples=min_samples, **kwargs)
        self.model.fit(X)
        logger.info(f"DBSCAN 训练完成 (eps={eps}, min_samples={min_samples})")
    
    def predict(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测异常
        
        Args:
            data: 待检测数据
            
        Returns:
            (predictions, scores)
            predictions: 1=正常，-1=异常
            scores: 异常得分 (越低越异常)
        """
        if not self.is_fitted:
            raise RuntimeError("模型未训练，请先调用 fit() 方法")
        
        # 数据预处理
        X = data.dropna().values
        X_scaled = self.scaler.transform(X)
        
        if isinstance(self.model, IsolationForest):
            predictions = self.model.predict(X_scaled)
            scores = self.model.score_samples(X_scaled)
        else:
            # DBSCAN 等其他算法
            predictions = self.model.fit_predict(X_scaled)
            scores = -np.abs(predictions)  # 简化处理
        
        return predictions, scores
    
    def detect(self, data: pd.DataFrame, threshold: Optional[float] = None) -> pd.DataFrame:
        """
        检测异常并返回详细信息
        
        Args:
            data: 待检测数据
            threshold: 自定义阈值 (可选)
            
        Returns:
            DataFrame，包含检测结果
        """
        predictions, scores = self.predict(data)
        
        result = pd.DataFrame({
            'timestamp': data.index if hasattr(data, 'index') else range(len(data)),
            'prediction': predictions,
            'anomaly_score': scores,
            'is_anomaly': predictions == -1
        })
        
        # 应用自定义阈值
        if threshold is not None:
            result['is_anomaly'] = scores < threshold
        
        # 统计信息
        anomaly_count = result['is_anomaly'].sum()
        total_count = len(result)
        anomaly_rate = anomaly_count / total_count * 100
        
        logger.info(f"异常检测完成：{anomaly_count}/{total_count} ({anomaly_rate:.2f}%)")
        
        return result
    
    def get_anomalies(self, data: pd.DataFrame) -> pd.DataFrame:
        """仅返回异常点"""
        result = self.detect(data)
        return result[result['is_anomaly']]
    
    def save(self, model_path: str):
        """保存模型"""
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'method': self.method,
            'model': self.model,
            'scaler': self.scaler,
            'config': self.config
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"模型已保存：{model_path}")
    
    def load(self, model_path: str):
        """加载模型"""
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"模型文件不存在：{model_path}")
        
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.method = model_data['method']
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.config = model_data['config']
        self.is_fitted = True
        
        logger.info(f"模型已加载：{model_path}")


# 使用示例
if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 1000
    
    # 正常数据
    normal_data = np.random.randn(n_samples, 3) * [1, 2, 0.5] + [5, 10, 20]
    
    # 添加异常点
    anomaly_indices = np.random.choice(n_samples, 50, replace=False)
    normal_data[anomaly_indices] += np.random.randn(50, 3) * [5, 10, 5] + [10, 30, 40]
    
    # 创建 DataFrame
    df = pd.DataFrame(normal_data, columns=['DO', 'pH', 'COD'])
    df.index = pd.date_range('2026-03-24', periods=n_samples, freq='10T')
    
    # 训练模型
    detector = AnomalyDetector(method='isolation_forest')
    detector.fit(df)
    
    # 检测异常
    anomalies = detector.get_anomalies(df)
    
    print(f"\n检测到 {len(anomalies)} 个异常点:")
    print(anomalies.head())
    
    # 可视化
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # 原始数据
    for col in df.columns:
        axes[0].plot(df.index, df[col], label=col, alpha=0.7)
    axes[0].set_title('原始数据')
    axes[0].legend()
    axes[0].grid(True)
    
    # 异常得分
    result = detector.detect(df)
    axes[1].plot(result['timestamp'], result['anomaly_score'], label='Anomaly Score', color='blue')
    axes[1].scatter(
        result[result['is_anomaly']]['timestamp'],
        result[result['is_anomaly']]['anomaly_score'],
        color='red',
        label='Anomaly',
        s=50
    )
    axes[1].axhline(y=result['anomaly_score'].quantile(0.05), color='r', linestyle='--', label='Threshold')
    axes[1].set_title('异常检测结果')
    axes[1].legend()
    axes[1].grid(True)
    
    plt.tight_layout()
    plt.savefig('anomaly_detection_result.png')
    print("\n结果已保存至：anomaly_detection_result.png")
