"""
评估指标计算工具
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    计算分类/回归指标
    
    Args:
        y_true: 真实值
        y_pred: 预测值
        
    Returns:
        指标字典
    """
    metrics = {}
    
    # 回归指标
    if len(y_true.shape) == 1 or y_true.shape[1] == 1:
        # MAE
        mae = np.mean(np.abs(y_true - y_pred))
        metrics['mae'] = float(mae)
        
        # RMSE
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        metrics['rmse'] = float(rmse)
        
        # MAPE
        mask = y_true != 0
        if mask.any():
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
            metrics['mape'] = float(mape)
    
    return metrics


def confusion_matrix_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    计算混淆矩阵相关指标 (用于异常检测)
    
    Args:
        y_true: 真实标签 (1=正常，-1=异常)
        y_pred: 预测标签
        
    Returns:
        指标字典
    """
    # 转换为二分类 (1=异常，0=正常)
    y_true_binary = (y_true == -1).astype(int)
    y_pred_binary = (y_pred == -1).astype(int)
    
    # TP, FP, TN, FN
    tp = np.sum((y_true_binary == 1) & (y_pred_binary == 1))
    fp = np.sum((y_true_binary == 0) & (y_pred_binary == 1))
    tn = np.sum((y_true_binary == 0) & (y_pred_binary == 0))
    fn = np.sum((y_true_binary == 1) & (y_pred_binary == 0))
    
    # 计算指标
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0
    
    return {
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1_score),
        'accuracy': float(accuracy),
        'confusion_matrix': {
            'tp': int(tp),
            'fp': int(fp),
            'tn': int(tn),
            'fn': int(fn)
        }
    }


def rule_engine_metrics(triggered_rules: List[Dict[str, Any]], total_evaluations: int) -> Dict[str, float]:
    """
    计算规则引擎指标
    
    Args:
        triggered_rules: 触发的规则列表
        total_evaluations: 总评估次数
        
    Returns:
        指标字典
    """
    if total_evaluations == 0:
        return {'trigger_rate': 0.0}
    
    trigger_rate = len(triggered_rules) / total_evaluations * 100
    
    # 按严重程度统计
    severity_counts = {}
    for rule in triggered_rules:
        severity = rule.get('severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    return {
        'trigger_rate': float(trigger_rate),
        'total_triggers': len(triggered_rules),
        'by_severity': severity_counts
    }


# 使用示例
if __name__ == "__main__":
    # 测试回归指标
    y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred = np.array([1.1, 1.9, 3.2, 3.8, 5.1])
    
    metrics = calculate_metrics(y_true, y_pred)
    print("回归指标:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    
    # 测试分类指标
    y_true_cls = np.array([1, 1, -1, -1, 1, -1])
    y_pred_cls = np.array([1, -1, -1, -1, 1, 1])
    
    cls_metrics = confusion_matrix_metrics(y_true_cls, y_pred_cls)
    print("\n分类指标:")
    for k, v in cls_metrics.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v:.4f}")
