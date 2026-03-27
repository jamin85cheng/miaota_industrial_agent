"""
数据压缩模块

功能需求: S-03 数据压缩 - 自动压缩历史数据
作者: Data Team
"""

import zlib
import gzip
import struct
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class CompressedData:
    """压缩后的数据结构"""
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: str
    data: bytes
    metadata: Dict[str, Any]


class TimeSeriesCompressor:
    """
    时序数据压缩器
    
    支持算法:
    1. Delta Encoding + ZigZag + VarInt (时序数据专用)
    2. Gorilla Compression (Facebook, float专用)
    3. Snappy (快速压缩)
    4. GZIP (高压缩率)
    """
    
    def __init__(self, algorithm: str = "delta"):
        """
        初始化压缩器
        
        Args:
            algorithm: 压缩算法 (delta/gorilla/snappy/gzip)
        """
        self.algorithm = algorithm
        
    def compress(self, timestamps: List[datetime], 
                 values: List[float]) -> CompressedData:
        """
        压缩时序数据
        
        Args:
            timestamps: 时间戳列表
            values: 值列表
            
        Returns:
            压缩后的数据
        """
        if self.algorithm == "delta":
            return self._compress_delta(timestamps, values)
        elif self.algorithm == "gorilla":
            return self._compress_gorilla(timestamps, values)
        elif self.algorithm == "gzip":
            return self._compress_gzip(timestamps, values)
        else:
            raise ValueError(f"不支持的压缩算法: {self.algorithm}")
    
    def _compress_delta(self, timestamps: List[datetime], 
                        values: List[float]) -> CompressedData:
        """
        Delta + ZigZag + VarInt 压缩
        
        适用于整数时间戳和浮点数值
        """
        original_size = len(timestamps) * 16  # 假设8字节时间戳 + 8字节浮点
        
        # 转换为整数时间戳 (毫秒)
        ts_ints = [int(ts.timestamp() * 1000) for ts in timestamps]
        
        # Delta 编码时间戳
        ts_deltas = [ts_ints[0]]
        for i in range(1, len(ts_ints)):
            ts_deltas.append(ts_ints[i] - ts_ints[i-1])
        
        # Delta 编码值 (乘1000转为整数)
        value_ints = [int(v * 1000) for v in values]
        value_deltas = [value_ints[0]]
        for i in range(1, len(value_ints)):
            value_deltas.append(value_ints[i] - value_ints[i-1])
        
        # ZigZag 编码 (处理负数)
        def zigzag_encode(n: int) -> int:
            return (n << 1) ^ (n >> 63)
        
        ts_encoded = [zigzag_encode(d) for d in ts_deltas]
        value_encoded = [zigzag_encode(d) for d in value_deltas]
        
        # VarInt 编码并打包
        data_bytes = self._pack_varints(ts_encoded + value_encoded)
        
        # 添加头部信息
        header = struct.pack('>III', len(timestamps), ts_ints[0], value_ints[0])
        compressed = header + data_bytes
        
        compressed_size = len(compressed)
        
        return CompressedData(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=original_size / max(compressed_size, 1),
            algorithm="delta",
            data=compressed,
            metadata={
                'count': len(timestamps),
                'start_time': timestamps[0].isoformat(),
                'end_time': timestamps[-1].isoformat()
            }
        )
    
    def _pack_varints(self, numbers: List[int]) -> bytes:
        """VarInt 编码"""
        result = bytearray()
        for num in numbers:
            while num >= 0x80:
                result.append((num & 0x7f) | 0x80)
                num >>= 7
            result.append(num)
        return bytes(result)
    
    def _compress_gorilla(self, timestamps: List[datetime], 
                          values: List[float]) -> CompressedData:
        """
        Gorilla 压缩算法 (Facebook)
        
        专门针对浮点数时序数据的压缩算法
        """
        original_size = len(timestamps) * 16
        
        # 简化实现：使用 numpy 的精度压缩
        # 实际 Gorilla 算法需要位操作实现
        values_array = np.array(values, dtype=np.float32)
        
        # 打包时间戳和值
        ts_array = np.array([ts.timestamp() for ts in timestamps], dtype=np.float64)
        
        # 使用 numpy 的 save 压缩
        buffer = bytearray()
        np.save(buffer, ts_array, allow_pickle=False)
        np.save(buffer, values_array, allow_pickle=False)
        
        # GZIP 压缩
        compressed = gzip.compress(bytes(buffer), compresslevel=6)
        
        return CompressedData(
            original_size=original_size,
            compressed_size=len(compressed),
            compression_ratio=original_size / max(len(compressed), 1),
            algorithm="gorilla",
            data=compressed,
            metadata={'count': len(timestamps)}
        )
    
    def _compress_gzip(self, timestamps: List[datetime], 
                       values: List[float]) -> CompressedData:
        """GZIP 压缩"""
        original_size = len(timestamps) * 16
        
        # 打包为 JSON
        import json
        data = {
            'timestamps': [ts.isoformat() for ts in timestamps],
            'values': values
        }
        json_bytes = json.dumps(data).encode('utf-8')
        
        # GZIP 压缩
        compressed = gzip.compress(json_bytes, compresslevel=9)
        
        return CompressedData(
            original_size=original_size,
            compressed_size=len(compressed),
            compression_ratio=original_size / max(len(compressed), 1),
            algorithm="gzip",
            data=compressed,
            metadata={'count': len(timestamps)}
        )
    
    def decompress(self, compressed: CompressedData) -> Tuple[List[datetime], List[float]]:
        """解压缩数据"""
        if compressed.algorithm == "delta":
            return self._decompress_delta(compressed.data)
        elif compressed.algorithm == "gorilla":
            return self._decompress_gorilla(compressed.data)
        elif compressed.algorithm == "gzip":
            return self._decompress_gzip(compressed.data)
        else:
            raise ValueError(f"不支持的解压算法: {compressed.algorithm}")
    
    def _decompress_delta(self, data: bytes) -> Tuple[List[datetime], List[float]]:
        """解压缩 Delta 编码数据"""
        # 解析头部
        count, ts_base, value_base = struct.unpack('>III', data[:12])
        
        # 解压 VarInts
        numbers = self._unpack_varints(data[12:])
        
        # 分离时间戳和值的 deltas
        ts_deltas = numbers[:count]
        value_deltas = numbers[count:]
        
        # ZigZag 解码
        def zigzag_decode(n: int) -> int:
            return (n >> 1) ^ -(n & 1)
        
        ts_deltas = [zigzag_decode(d) for d in ts_deltas]
        value_deltas = [zigzag_decode(d) for d in value_deltas]
        
        # Delta 解码
        timestamps = [ts_base]
        for d in ts_deltas[1:]:
            timestamps.append(timestamps[-1] + d)
        
        values = [value_base]
        for d in value_deltas[1:]:
            values.append(values[-1] + d)
        
        # 转换回 datetime 和 float
        timestamps = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]
        values = [v / 1000 for v in values]
        
        return timestamps, values
    
    def _unpack_varints(self, data: bytes) -> List[int]:
        """VarInt 解码"""
        numbers = []
        i = 0
        while i < len(data):
            num = 0
            shift = 0
            while True:
                byte = data[i]
                i += 1
                num |= (byte & 0x7f) << shift
                if (byte & 0x80) == 0:
                    break
                shift += 7
            numbers.append(num)
        return numbers
    
    def _decompress_gorilla(self, data: bytes) -> Tuple[List[datetime], List[float]]:
        """解压缩 Gorilla 数据"""
        decompressed = gzip.decompress(data)
        buffer = bytes(decompressed)
        
        # 读取 numpy 数组
        from io import BytesIO
        stream = BytesIO(buffer)
        ts_array = np.load(stream, allow_pickle=False)
        values_array = np.load(stream, allow_pickle=False)
        
        timestamps = [datetime.fromtimestamp(ts) for ts in ts_array]
        values = values_array.tolist()
        
        return timestamps, values
    
    def _decompress_gzip(self, data: bytes) -> Tuple[List[datetime], List[float]]:
        """解压缩 GZIP 数据"""
        import json
        decompressed = gzip.decompress(data)
        data_dict = json.loads(decompressed.decode('utf-8'))
        
        timestamps = [datetime.fromisoformat(ts) for ts in data_dict['timestamps']]
        values = data_dict['values']
        
        return timestamps, values


class CompressionScheduler:
    """
    压缩调度器
    
    自动压缩历史数据
    """
    
    def __init__(self, storage_backend, compress_after_days: int = 7):
        """
        初始化调度器
        
        Args:
            storage_backend: 存储后端
            compress_after_days: 超过多少天的数据自动压缩
        """
        self.storage = storage_backend
        self.compress_after_days = compress_after_days
        self.compressor = TimeSeriesCompressor(algorithm="delta")
    
    async def run_compression_task(self):
        """运行压缩任务"""
        logger.info("启动数据压缩任务")
        
        # 计算需要压缩的时间范围
        end_time = datetime.now() - timedelta(days=self.compress_after_days)
        start_time = end_time - timedelta(days=30)  # 每次压缩30天的数据
        
        # TODO: 从存储中查询数据并压缩
        # 这里需要与具体存储后端集成
        
        logger.info(f"压缩任务完成: {start_time} 到 {end_time}")
    
    def estimate_compression_ratio(self, sample_data: List[float]) -> float:
        """
        估算压缩率
        
        Args:
            sample_data: 样本数据
            
        Returns:
            压缩率 (原始大小/压缩后大小)
        """
        timestamps = [datetime.now() - timedelta(minutes=i) for i in range(len(sample_data))]
        
        compressed = self.compressor.compress(timestamps, sample_data)
        
        return compressed.compression_ratio


# 使用示例
if __name__ == "__main__":
    # 生成测试数据
    timestamps = [datetime.now() - timedelta(minutes=i*5) for i in range(1000)]
    values = [3.5 + i*0.01 + (i % 10) * 0.1 for i in range(1000)]
    
    # 测试不同算法
    for algo in ["delta", "gorilla", "gzip"]:
        compressor = TimeSeriesCompressor(algorithm=algo)
        compressed = compressor.compress(timestamps, values)
        
        print(f"\n{algo.upper()} 压缩:")
        print(f"  原始大小: {compressed.original_size} bytes")
        print(f"  压缩后: {compressed.compressed_size} bytes")
        print(f"  压缩率: {compressed.compression_ratio:.2f}x")
        
        # 验证解压
        ts_decompressed, values_decompressed = compressor.decompress(compressed)
        print(f"  解压验证: {len(ts_decompressed)} 条数据")
