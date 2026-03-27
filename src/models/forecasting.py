"""
时序预测模块

功能：
- 短期趋势预测 (未来几分钟到几小时)
- 长期趋势预测 (未来几天到几周)
- 多变量预测
- 不确定性量化

支持的模型：
- Prophet (Facebook, 适合业务时间序列)
- NeuralProphet (深度学习版 Prophet)
- ARIMA (传统统计方法)
- LSTM (深度学习)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from loguru import logger


class TimeSeriesForecaster:
    """时序预测器基类"""
    
    def fit(self, df: pd.DataFrame, target_col: str):
        """训练模型"""
        raise NotImplementedError
    
    def predict(self, periods: int) -> pd.DataFrame:
        """预测未来"""
        raise NotImplementedError
    
    def evaluate(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """评估预测效果"""
        mae = np.mean(np.abs(actual - predicted))
        mse = np.mean((actual - predicted) ** 2)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((actual - predicted) / (actual + 1e-8))) * 100
        
        return {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "mape": mape
        }


class ProphetForecaster(TimeSeriesForecaster):
    """Prophet 预测器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = None
        self.target_col = None
        self.history = None
    
    def fit(self, df: pd.DataFrame, target_col: str):
        """训练 Prophet 模型"""
        try:
            from prophet import Prophet
            
            # 准备数据 (Prophet 需要 ds 和 y 列)
            if not isinstance(df.index, pd.DatetimeIndex):
                df = df.copy()
                df.index = pd.to_datetime(df.index)
            
            prophet_df = pd.DataFrame({
                'ds': df.index,
                'y': df[target_col].values
            })
            
            # 添加协变量 (如果有)
            for col in df.columns:
                if col != target_col and col not in ['ds', 'y']:
                    prophet_df[col] = df[col].values
            
            # 初始化模型
            self.model = Prophet(
                yearly_seasonality=self.config.get('yearly_seasonality', 'auto'),
                weekly_seasonality=self.config.get('weekly_seasonality', 'auto'),
                daily_seasonality=self.config.get('daily_seasonality', True),
                changepoint_prior_scale=self.config.get('changepoint_prior_scale', 0.05),
                interval_width=self.config.get('interval_width', 0.95)
            )
            
            # 添加协变量
            for col in prophet_df.columns:
                if col not in ['ds', 'y']:
                    self.model.add_regressor(col)
            
            # 训练
            self.model.fit(prophet_df)
            self.history = prophet_df
            self.target_col = target_col
            
            logger.info(f"Prophet 模型训练完成，样本数：{len(df)}")
            
        except ImportError:
            logger.error("缺少 prophet 依赖：pip install prophet")
            raise
        except Exception as e:
            logger.error(f"Prophet 训练失败：{e}")
            raise
    
    def predict(self, periods: int, freq: str = 'H') -> pd.DataFrame:
        """预测未来"""
        if self.model is None:
            raise ValueError("模型未训练")
        
        # 创建未来数据框
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        
        # 填充协变量 (用最后已知值)
        for col in self.history.columns:
            if col not in ['ds', 'y'] and col in future.columns:
                last_value = self.history[col].iloc[-1]
                future[col] = last_value
        
        # 预测
        forecast = self.model.predict(future)
        
        logger.info(f"Prophet 预测未来 {periods} 个时间点")
        return forecast
    
    def get_components(self) -> pd.DataFrame:
        """获取预测组件 (趋势、季节性等)"""
        if self.model is None:
            raise ValueError("模型未训练")
        
        from prophet.plot import plot_components_plotly
        
        return self.model.plot_components(self.model.predict(self.history))


class NeuralProphetForecaster(TimeSeriesForecaster):
    """NeuralProphet 预测器 (深度学习)"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = None
        self.target_col = None
    
    def fit(self, df: pd.DataFrame, target_col: str):
        """训练 NeuralProphet 模型"""
        try:
            from neuralprophet import NeuralProphet
            
            # 准备数据
            if not isinstance(df.index, pd.DatetimeIndex):
                df = df.copy()
                df.index = pd.to_datetime(df.index)
            
            neural_df = pd.DataFrame({
                'ds': df.index,
                'y': df[target_col].values
            })
            
            # 初始化模型
            self.model = NeuralProphet(
                yearly_seasonality=self.config.get('yearly_seasonality', 'auto'),
                weekly_seasonality=self.config.get('weekly_seasonality', 'auto'),
                daily_seasonality=self.config.get('daily_seasonality', True),
                n_forecasts=self.config.get('n_forecasts', 1),
                n_lags=self.config.get('n_lags', 10),
                learning_rate=self.config.get('learning_rate', 0.001),
                epochs=self.config.get('epochs', 100),
                batch_size=self.config.get('batch_size', 32),
                loss_func=self.config.get('loss_func', 'Huber')
            )
            
            # 训练
            metrics = self.model.fit(neural_df, freq='H', validation_split=0.2)
            self.target_col = target_col
            
            logger.info(f"NeuralProphet 训练完成，最终 loss: {metrics['Loss'].iloc[-1]:.4f}")
            
        except ImportError:
            logger.error("缺少 neuralprophet 依赖：pip install neuralprophet")
            raise
        except Exception as e:
            logger.error(f"NeuralProphet 训练失败：{e}")
            raise
    
    def predict(self, periods: int, freq: str = 'H') -> pd.DataFrame:
        """预测未来"""
        if self.model is None:
            raise ValueError("模型未训练")
        
        # 创建未来数据框
        future = self.model.make_future_dataframe(self.history, periods=periods)
        
        # 预测
        forecast = self.model.predict(future)
        
        logger.info(f"NeuralProphet 预测未来 {periods} 个时间点")
        return forecast


class ARIMAForecaster(TimeSeriesForecaster):
    """ARIMA 预测器"""
    
    def __init__(self, order: Tuple[int, int, int] = (1, 1, 1),
                 seasonal_order: Tuple[int, int, int, int] = (0, 0, 0, 0)):
        self.order = order
        self.seasonal_order = seasonal_order
        self.model = None
        self.target_col = None
    
    def fit(self, df: pd.DataFrame, target_col: str):
        """训练 ARIMA 模型"""
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            
            data = df[target_col].values
            
            # SARIMAX 模型
            self.model = SARIMAX(
                data,
                order=self.order,
                seasonal_order=self.seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            
            fitted_model = self.model.fit(disp=False)
            self.target_col = target_col
            
            logger.info(f"ARIMA 模型训练完成，AIC: {fitted_model.aic:.2f}")
            
        except ImportError:
            logger.error("缺少 statsmodels 依赖：pip install statsmodels")
            raise
        except Exception as e:
            logger.error(f"ARIMA 训练失败：{e}")
            raise
    
    def predict(self, periods: int, freq: str = 'H') -> pd.DataFrame:
        """预测未来"""
        if self.model is None:
            raise ValueError("模型未训练")
        
        # 预测
        forecast = self.model.forecast(steps=periods)
        
        # 创建 DataFrame
        last_date = pd.Timestamp.now()
        dates = pd.date_range(start=last_date, periods=periods, freq=freq)
        
        result_df = pd.DataFrame({
            'ds': dates,
            'yhat': forecast
        })
        
        logger.info(f"ARIMA 预测未来 {periods} 个时间点")
        return result_df


class LSTMForecaster(TimeSeriesForecaster):
    """LSTM 深度学习预测器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = None
        self.scaler = None
        self.lookback = self.config.get('lookback', 60)
        self.target_col = None
    
    def _create_sequences(self, data: np.ndarray, target: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """创建序列样本"""
        X, y = [], []
        for i in range(len(data) - self.lookback):
            X.append(data[i:i + self.lookback])
            y.append(target[i + self.lookback])
        return np.array(X), np.array(y)
    
    def fit(self, df: pd.DataFrame, target_col: str):
        """训练 LSTM 模型"""
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from tensorflow.keras.callbacks import EarlyStopping
            from sklearn.preprocessing import MinMaxScaler
            
            # 数据预处理
            data = df[[target_col]].values.astype(float)
            
            # 标准化
            self.scaler = MinMaxScaler()
            scaled_data = self.scaler.fit_transform(data)
            
            # 创建序列
            X, y = self._create_sequences(scaled_data, scaled_data)
            
            # 划分训练集
            split = int(len(X) * 0.8)
            X_train, y_train = X[:split], y[:split]
            
            # 构建模型
            self.model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(self.lookback, 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            self.model.compile(optimizer='adam', loss='mean_squared_error')
            
            # 训练
            early_stop = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)
            
            history = self.model.fit(
                X_train, y_train,
                epochs=self.config.get('epochs', 50),
                batch_size=self.config.get('batch_size', 32),
                callbacks=[early_stop],
                verbose=0
            )
            
            self.target_col = target_col
            
            logger.info(f"LSTM 训练完成，最终 loss: {history.history['loss'][-1]:.6f}")
            
        except ImportError:
            logger.error("缺少 tensorflow 依赖：pip install tensorflow")
            raise
        except Exception as e:
            logger.error(f"LSTM 训练失败：{e}")
            raise
    
    def predict(self, periods: int, freq: str = 'H') -> pd.DataFrame:
        """预测未来"""
        if self.model is None:
            raise ValueError("模型未训练")
        
        predictions = []
        current_sequence = self.last_sequence.copy()
        
        for _ in range(periods):
            # 预测下一步
            pred = self.model.predict(current_sequence.reshape(1, self.lookback, 1), verbose=0)[0, 0]
            predictions.append(pred)
            
            # 更新序列
            current_sequence = np.roll(current_sequence, -1)
            current_sequence[-1] = pred
        
        # 反标准化
        predictions = np.array(predictions).reshape(-1, 1)
        predictions = self.scaler.inverse_transform(predictions).flatten()
        
        # 创建 DataFrame
        dates = pd.date_range(start=pd.Timestamp.now(), periods=periods, freq=freq)
        
        result_df = pd.DataFrame({
            'ds': dates,
            'yhat': predictions
        })
        
        logger.info(f"LSTM 预测未来 {periods} 个时间点")
        return result_df


class EnsembleForecaster:
    """集成预测器 (多模型融合)"""
    
    def __init__(self, models: List[Tuple[str, TimeSeriesForecaster]],
                 weights: Optional[List[float]] = None):
        self.models = models  # [(name, forecaster), ...]
        self.weights = weights or [1.0 / len(models)] * len(models)
        self.target_col = None
    
    def fit_all(self, df: pd.DataFrame, target_col: str):
        """训练所有模型"""
        self.target_col = target_col
        
        for name, forecaster in self.models:
            logger.info(f"训练模型：{name}")
            try:
                forecaster.fit(df, target_col)
                logger.info(f"✓ {name} 训练完成")
            except Exception as e:
                logger.error(f"✗ {name} 训练失败：{e}")
    
    def predict(self, periods: int, freq: str = 'H') -> pd.DataFrame:
        """集成预测"""
        predictions = []
        
        for (name, forecaster), weight in zip(self.models, self.weights):
            try:
                pred_df = forecaster.predict(periods, freq)
                predictions.append(pred_df['yhat'].values * weight)
            except Exception as e:
                logger.warning(f"{name} 预测失败：{e}")
        
        # 加权平均
        ensemble_pred = np.sum(predictions, axis=0)
        
        dates = pd.date_range(start=pd.Timestamp.now(), periods=periods, freq=freq)
        
        result_df = pd.DataFrame({
            'ds': dates,
            'yhat': ensemble_pred
        })
        
        logger.info(f"集成预测完成，模型数：{len(predictions)}")
        return result_df


# 测试代码
if __name__ == "__main__":
    # 生成测试数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='H')
    
    # 带趋势和季节性的模拟数据
    trend = np.linspace(100, 150, 1000)
    seasonal = 20 * np.sin(np.linspace(0, 8 * np.pi, 1000))
    noise = np.random.randn(1000) * 5
    values = trend + seasonal + noise
    
    df = pd.DataFrame({'temperature': values}, index=dates)
    
    print("测试数据:")
    print(df.head())
    print(f"形状：{df.shape}")
    
    # 测试 ARIMA
    print("\n=== 测试 ARIMA ===")
    try:
        arima = ARIMAForecaster(order=(2, 1, 2))
        arima.fit(df, 'temperature')
        forecast = arima.predict(periods=24, freq='H')
        print(f"ARIMA 预测未来 24 小时:")
        print(forecast.head())
    except Exception as e:
        print(f"ARIMA 测试跳过：{e}")
    
    # 测试 Prophet
    print("\n=== 测试 Prophet ===")
    try:
        prophet = ProphetForecaster({'daily_seasonality': True})
        prophet.fit(df, 'temperature')
        forecast = prophet.predict(periods=24, freq='H')
        print(f"Prophet 预测未来 24 小时:")
        print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].head())
    except Exception as e:
        print(f"Prophet 测试跳过：{e}")
