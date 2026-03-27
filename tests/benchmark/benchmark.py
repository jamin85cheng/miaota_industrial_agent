"""
性能基准测试

测试各模块的性能指标
"""

import time
import statistics
import asyncio
import concurrent.futures
from dataclasses import dataclass
from typing import List, Dict, Callable, Any
from datetime import datetime
import json


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    ops_per_second: float


class BenchmarkRunner:
    """基准测试运行器"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    def run(self, name: str, func: Callable, iterations: int = 1000, 
            warmup: int = 100) -> BenchmarkResult:
        """
        运行基准测试
        
        Args:
            name: 测试名称
            func: 测试函数
            iterations: 迭代次数
            warmup: 预热次数
        
        Returns:
            BenchmarkResult: 测试结果
        """
        print(f"\n运行基准测试: {name}")
        print(f"  预热: {warmup} 次")
        print(f"  迭代: {iterations} 次")
        
        # 预热
        for _ in range(warmup):
            func()
        
        # 正式测试
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            func()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        # 计算统计值
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            ops_per_second=iterations / sum(times)
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    def run_async(self, name: str, func: Callable, iterations: int = 1000) -> BenchmarkResult:
        """运行异步基准测试"""
        async def runner():
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                await func()
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            return times
        
        times = asyncio.run(runner())
        
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            ops_per_second=iterations / sum(times)
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    def _print_result(self, result: BenchmarkResult):
        """打印结果"""
        print(f"  总时间: {result.total_time:.3f}s")
        print(f"  平均: {result.avg_time*1000:.3f}ms")
        print(f"  最小: {result.min_time*1000:.3f}ms")
        print(f"  最大: {result.max_time*1000:.3f}ms")
        print(f"  标准差: {result.std_dev*1000:.3f}ms")
        print(f"  吞吐量: {result.ops_per_second:.2f} ops/s")
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "total_iterations": sum(r.iterations for r in self.results),
                "total_time": sum(r.total_time for r in self.results)
            },
            "results": [
                {
                    "name": r.name,
                    "iterations": r.iterations,
                    "avg_time_ms": round(r.avg_time * 1000, 3),
                    "ops_per_second": round(r.ops_per_second, 2),
                    "latency_p99_ms": round(r.max_time * 1000, 3)
                }
                for r in self.results
            ]
        }
    
    def save_report(self, filename: str = "benchmark_report.json"):
        """保存报告"""
        report = self.generate_report()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n报告已保存: {filename}")


def benchmark_input_validation():
    """测试输入验证性能"""
    from security.input_validator import InputValidator
    
    runner = BenchmarkRunner()
    
    # 测试验证测量名称
    runner.run(
        "validate_measurement",
        lambda: InputValidator.validate_measurement("temperature_sensor_01"),
        iterations=10000
    )
    
    # 测试验证标签
    runner.run(
        "validate_tags",
        lambda: InputValidator.validate_tags({"device": "PLC001", "location": "车间A"}),
        iterations=10000
    )
    
    # 测试速率限制
    limiter = InputValidator.get_rate_limiter("test", max_requests=1000, window_seconds=60)
    runner.run(
        "rate_limiter",
        lambda: limiter.is_allowed("client_1"),
        iterations=10000
    )
    
    return runner


def benchmark_thread_safe():
    """测试线程安全性能"""
    from src.utils.thread_safe import SafeValue, ThreadSafeDict
    
    runner = BenchmarkRunner()
    
    # 测试SafeValue
    safe_value = SafeValue(0)
    runner.run(
        "safe_value_get",
        lambda: safe_value.get(),
        iterations=100000
    )
    
    runner.run(
        "safe_value_set",
        lambda: safe_value.set(42),
        iterations=100000
    )
    
    # 测试ThreadSafeDict
    safe_dict = ThreadSafeDict()
    safe_dict.set("key", "value")
    runner.run(
        "safe_dict_get",
        lambda: safe_dict.get("key"),
        iterations=100000
    )
    
    runner.run(
        "safe_dict_set",
        lambda: safe_dict.set("key", "value"),
        iterations=100000
    )
    
    return runner


def benchmark_data_processing():
    """测试数据处理性能"""
    import random
    from datetime import datetime, timedelta
    
    runner = BenchmarkRunner()
    
    # 生成测试数据
    data_points = []
    base_time = datetime.utcnow()
    for i in range(10000):
        data_points.append({
            "timestamp": base_time + timedelta(seconds=i),
            "value": random.gauss(50, 10)
        })
    
    # 测试数据聚合
    def aggregate_data():
        values = [p["value"] for p in data_points]
        return {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values)
        }
    
    runner.run(
        "data_aggregation_10k",
        aggregate_data,
        iterations=1000
    )
    
    # 测试数据序列化
    def serialize_data():
        return json.dumps(data_points[:100])  # 只序列化100条
    
    runner.run(
        "json_serialize_100",
        serialize_data,
        iterations=10000
    )
    
    return runner


def benchmark_anomaly_detection():
    """测试异常检测算法性能"""
    import random
    import math
    import statistics
    
    runner = BenchmarkRunner()
    
    # 生成测试数据
    data = [random.gauss(50, 10) for _ in range(1000)]
    
    # 测试Z-Score检测
    def zscore_detection():
        mean = statistics.mean(data)
        std = statistics.stdev(data)
        threshold = 2.5
        anomalies = []
        for value in data:
            z_score = abs((value - mean) / std) if std > 0 else 0
            if z_score > threshold:
                anomalies.append(value)
        return anomalies
    
    runner.run(
        "zscore_detection_1k",
        zscore_detection,
        iterations=1000
    )
    
    return runner


def benchmark_api_response():
    """模拟API响应性能"""
    import json
    
    runner = BenchmarkRunner()
    
    # 模拟设备列表响应
    devices = [
        {
            "id": f"DEV_{i:03d}",
            "name": f"Device {i}",
            "type": "s7",
            "status": "online",
            "tags": [{"name": "temp", "value": 25.5}]
        }
        for i in range(100)
    ]
    
    def serialize_response():
        return json.dumps({"total": 100, "devices": devices})
    
    runner.run(
        "serialize_device_list_100",
        serialize_response,
        iterations=10000
    )
    
    # 模拟告警查询响应
    alerts = [
        {
            "id": f"ALT_{i:04d}",
            "severity": "warning",
            "message": f"Alert message {i}",
            "created_at": datetime.now().isoformat()
        }
        for i in range(50)
    ]
    
    def serialize_alerts():
        return json.dumps({"total": 50, "alerts": alerts})
    
    runner.run(
        "serialize_alerts_50",
        serialize_alerts,
        iterations=10000
    )
    
    return runner


def run_all_benchmarks():
    """运行所有基准测试"""
    print("=" * 60)
    print("性能基准测试")
    print("=" * 60)
    
    all_results = []
    
    # 输入验证测试
    print("\n" + "=" * 60)
    print("1. 输入验证性能测试")
    print("=" * 60)
    try:
        runner = benchmark_input_validation()
        all_results.extend(runner.results)
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 线程安全测试
    print("\n" + "=" * 60)
    print("2. 线程安全性能测试")
    print("=" * 60)
    try:
        runner = benchmark_thread_safe()
        all_results.extend(runner.results)
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 数据处理测试
    print("\n" + "=" * 60)
    print("3. 数据处理性能测试")
    print("=" * 60)
    try:
        runner = benchmark_data_processing()
        all_results.extend(runner.results)
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 异常检测测试
    print("\n" + "=" * 60)
    print("4. 异常检测性能测试")
    print("=" * 60)
    try:
        runner = benchmark_anomaly_detection()
        all_results.extend(runner.results)
    except Exception as e:
        print(f"测试失败: {e}")
    
    # API响应测试
    print("\n" + "=" * 60)
    print("5. API响应性能测试")
    print("=" * 60)
    try:
        runner = benchmark_api_response()
        all_results.extend(runner.results)
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 生成总报告
    print("\n" + "=" * 60)
    print("测试完成 - 生成报告")
    print("=" * 60)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(all_results),
        "results": [
            {
                "name": r.name,
                "avg_time_ms": round(r.avg_time * 1000, 3),
                "ops_per_second": round(r.ops_per_second, 2)
            }
            for r in all_results
        ]
    }
    
    with open("benchmark_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n报告已保存: benchmark_report.json")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("性能摘要")
    print("=" * 60)
    
    # 按吞吐量排序
    sorted_results = sorted(all_results, key=lambda r: r.ops_per_second, reverse=True)
    print(f"\n最高吞吐量: {sorted_results[0].name} - {sorted_results[0].ops_per_second:.2f} ops/s")
    print(f"最低吞吐量: {sorted_results[-1].name} - {sorted_results[-1].ops_per_second:.2f} ops/s")
    
    avg_ops = statistics.mean([r.ops_per_second for r in all_results])
    print(f"平均吞吐量: {avg_ops:.2f} ops/s")


if __name__ == "__main__":
    run_all_benchmarks()
