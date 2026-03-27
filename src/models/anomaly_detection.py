"""
异常检测模块
支持 Isolation Forest、LSTM Autoencoder 等算法
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from loguru import logger
import joblib  # 用于模型保存

# 机器学习库
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn 未安装，异常检测功能受限")


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, method: str = 'isolation_forest', config: Optional[Dict[str, Any]] = None):
        """
        初始化异常检测器
        
        Args:
            method: 检测方法 ('isolation_forest', 'lstm_ae')
            config: 算法配置参数
        """
        self.method = method
        self.config = config or {}
        
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        # 特征列表
        self.features: List[str] = []
        
        # 阈值
        self.threshold = self.config.get('threshold', None)
        
        logger.info(f"异常检测器已初始化 (方法：{method})")
    
    def fit(self, data: pd.DataFrame, features: Optional[List[str]] = None):
        """
        训练模型
        
        Args:
            data: 训练数据 (DataFrame)
            features: 特征列名列表
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn 未安装，无法训练")
            return
        
        # 选择特征列
        if features:
            self.features = features
        else:
            self.features = data.select_dtypes(include=[np.number]).columns.tolist()
        
        logger.info(f"使用 {len(self.features)} 个特征进行训练：{self.features}")
        
        # 数据预处理
        X = data[self.features].dropna()
        
        if len(X) < 10:
            logger.error(f"训练数据不足 (当前：{len(X)} 行，至少需要 10 行)")
            return
        
        # 标准化
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练模型
        if self.method == 'isolation_forest':
            self._train_isolation_forest(X_scaled)
        elif self.method == 'lstm_ae':
            logger.warning("LSTM Autoencoder 暂未实现，使用 Isolation Forest 代替")
            self._train_isolation_forest(X_scaled)
        else:
            logger.error(f"不支持的检测方法：{self.method}")
            return
        
        self.is_trained = True
        logger.info("模型训练完成")
    
    def _train_isolation_forest(self, X_scaled: np.ndarray):
        """训练 Isolation Forest 模型"""
        contamination = self.config.get('contamination', 0.05)
        n_estimators = self.config.get('n_estimators', 100)
        random_state = self.config.get('random_state', 42)
        
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1  # 使用所有 CPU 核心
        )
        
        self.model.fit(X_scaled)
        logger.info(f"Isolation Forest 训练完成 (n_estimators={n_estimators})")
    
    def predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预测异常
        
        Args:
            data: 输入数据 (DataFrame)
            
        Returns:
            包含预测结果的 DataFrame
        """
        if not self.is_trained:
            logger.error("模型未训练，无法预测")
            return data
        
        # 提取特征
        X = data[self.features].copy()
        
        # 处理缺失值
        X = X.fillna(X.mean())
        
        # 标准化
        X_scaled = self.scaler.transform(X)
        
        # 预测
        predictions = self.model.predict(X_scaled)  # 1=正常，-1=异常
        scores = self.model.score_samples(X_scaled)  # 异常得分 (越低越异常)
        
        # 添加到结果中
        result = data.copy()
        result['is_anomaly'] = predictions == -1
        result['anomaly_score'] = scores
        result['anomaly_label'] = np.where(predictions == -1, '异常', '正常')
        
        return result
    
    def detect(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[int]]:
        """
        检测异常并返回异常点索引
        
        Args:
            data: 输入数据
            
        Returns:
            (结果 DataFrame, 异常点索引列表)
        """
        result = self.predict(data)
        anomaly_indices = result[result['is_anomaly']].index.tolist()
        
        return result, anomaly_indices
    
    def get_anomaly_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        获取异常统计摘要
        
        Args:
            data: 输入数据
            
        Returns:
            统计信息字典
        """
        result = self.predict(data)
        
        total_points = len(result)
        anomaly_count = result['is_anomaly'].sum()
        anomaly_rate = anomaly_count / total_points if total_points > 0 else 0
        
        # 按严重程度分组
        scores = result['anomaly_score']
        threshold_10pct = scores.quantile(0.1)  # 最异常的 10%
        severe_anomalies = result[scores <= threshold_10pct]
        
        return {
            'total_points': total_points,
            'anomaly_count': int(anomaly_count),
            'anomaly_rate': float(anomaly_rate),
            'severe_anomaly_count': len(severe_anomalies),
            'avg_anomaly_score': float(scores.mean()),
            'min_anomaly_score': float(scores.min()),
            'max_anomaly_score': float(scores.max()),
            'top_anomalies': severe_anomalies.index.tolist()[:10]  # Top 10 最异常点
        }
    
    def save_model(self, model_path: str):
        """保存模型"""
        if not self.is_trained:
            logger.warning("模型未训练，无法保存")
            return
        
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'features': self.features,
            'method': self.method,
            'config': self.config
        }
        
        joblib.dump(model_data, path)
        logger.info(f"模型已保存到：{path}")
    
    def load_model(self, model_path: str) -> bool:
        """加载模型"""
        path = Path(model_path)
        if not path.exists():
            logger.error(f"模型文件不存在：{path}")
            return False
        
        try:
            model_data = joblib.load(path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.features = model_data['features']
            self.method = model_data['method']
            self.config = model_data.get('config', {})
            self.is_trained = True
            
            logger.info(f"模型已从 {path} 加载")
            return True
            
        except Exception as e:
            logger.error(f"加载模型失败：{e}")
            return False
    
    def update_threshold(self, new_threshold: float):
        """更新异常判定阈值"""
        self.threshold = new_threshold
        logger.info(f"异常阈值已更新：{new_threshold}")


# 使用示例
if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 1000
    
    # 正常数据
    data = pd.DataFrame({
        'DO': np.random.normal(4.0, 0.5, n_samples),
        'pH': np.random.normal(7.2, 0.3, n_samples),
        'COD': np.random.normal(80, 10, n_samples),
        'temperature': np.random.normal(25, 2, n_samples)
    })
    
    # 注入异常点 (5%)
    n_anomalies = int(n_samples * 0.05)
    anomaly_indices = np.random.choice(n_samples, n_anomalies, replace=False)
    data.loc[anomaly_indices, 'DO'] = np.random.uniform(0.5, 1.5, n_anomalies)
    data.loc[anomaly_indices, 'COD'] = np.random.uniform(150, 200, n_anomalies)
    
    print(f"数据集形状：{data.shape}")
    print(f"注入异常点数：{n_anomalies}")
    
    # 创建检测器
    detector = AnomalyDetector(method='isolation_forest', config={
        'contamination': 0.05,
        'n_estimators': 100
    })
    
    # 训练模型 (用前 80% 数据)
    train_data = data.iloc[:int(len(data)*0.8)]
    detector.fit(train_data)
    
    # 预测 (用后 20% 数据)
    test_data = data.iloc[int(len(data)*0.8):]
    result, anomalies = detector.detect(test_data)
    
    print(f"\n检测结果:")
    print(f"  测试集大小：{len(test_data)}")
    print(f"  检测到的异常数：{len(anomalies)}")
    print(f"  异常率：{len(anomalies)/len(test_data)*100:.2f}%")
    
    # 获取统计摘要
    summary = detector.get_anomaly_summary(test_data)
    print(f"\n统计摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 保存模型
    detector.save_model('models/anomaly_detector.pkl')
    
    # 显示部分异常点
    if anomalies:
        print(f"\nTop 5 异常点:")
        top_5 = result.nsmallest(5, 'anomaly_score')
        print(top_5[['DO', 'pH', 'COD', 'temperature', 'anomaly_score']])
