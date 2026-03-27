"""
PLC 数据采集模块
支持西门子 S7 协议和 Modbus TCP 协议
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from loguru import logger
import pandas as pd

from src.utils.thread_safe import ConnectionGuard, SafeValue
from src.utils.error_handler import retry, ApplicationError, ExternalServiceError

# PLC 通信库 (需要安装：pip install python-snap7 pymodbus)
try:
    import snap7  # 西门子 S7
    from snap7.util import *
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    logger.warning("snap7 未安装，西门子 S7 采集功能不可用")

try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadDecoder
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    logger.warning("pymodbus 未安装，Modbus 采集功能不可用")


class PLCCollector:
    """PLC 数据采集器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器
        
        Args:
            config: 配置字典，包含 PLC 连接参数
        """
        self.config = config
        self.plc_type = config.get('type', 's7')  # 's7' 或 'modbus'
        self._client_guard = ConnectionGuard(f"PLC-{self.plc_type}")
        self._config = config
        self.scan_interval = config.get('scan_interval', 10)  # 采集间隔 (秒)
        self.tags = config.get('tags', [])  # 要采集的点位列表
        self.callbacks: List[Callable] = []  # 数据回调函数列表
        
        self._running = SafeValue(False)
        self._thread: Optional[threading.Thread] = None
        self._reconnect_attempts = SafeValue(0)
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 5  # 秒
        
        logger.info(f"PLC 采集器已初始化 (类型：{self.plc_type})")
    
    def connect(self) -> bool:
        """连接到 PLC"""
        try:
            if self.plc_type == 's7':
                return self._connect_s7()
            elif self.plc_type == 'modbus':
                return self._connect_modbus()
            else:
                logger.error(f"不支持的 PLC 类型：{self.plc_type}")
                return False
        except Exception as e:
            logger.error(f"连接 PLC 失败：{e}")
            return False
    
    def _connect_s7(self) -> bool:
        """连接西门子 S7 PLC"""
        if not SNAP7_AVAILABLE:
            logger.error("snap7 库未安装")
            return False
        
        try:
            self.client = snap7.client.Client()
            
            # S7-1200/1500 连接参数
            host = self.config.get('host', '192.168.1.100')
            port = self.config.get('port', 102)
            rack = self.config.get('rack', 0)
            slot = self.config.get('slot', 1)
            
            self.client.connect(host, rack, slot, port)
            
            if self.client.is_connected():
                self.is_connected = True
                logger.info(f"成功连接到西门子 S7 PLC ({host}:{port})")
                return True
            else:
                logger.error("S7 连接失败")
                return False
                
        except Exception as e:
            logger.error(f"S7 连接异常：{e}")
            return False
    
    def _connect_modbus(self) -> bool:
        """连接 Modbus TCP 设备"""
        if not MODBUS_AVAILABLE:
            logger.error("pymodbus 库未安装")
            return False
        
        try:
            host = self.config.get('host', '192.168.1.101')
            port = self.config.get('port', 502)
            
            self.client = ModbusTcpClient(host, port=port)
            
            if self.client.connect():
                self.is_connected = True
                logger.info(f"成功连接到 Modbus 设备 ({host}:{port})")
                return True
            else:
                logger.error("Modbus 连接失败")
                return False
                
        except Exception as e:
            logger.error(f"Modbus 连接异常：{e}")
            return False
    
    def disconnect(self):
        """断开 PLC 连接"""
        def cleanup_client(client):
            if self.plc_type == 's7':
                client.disconnect()
            elif self.plc_type == 'modbus':
                client.close()
        
        self._client_guard.disconnect(cleanup_client)
        self._running.set(False)
    
    def read_tag(self, tag_config: Dict[str, Any]) -> Optional[float]:
        """
        读取单个点位数据
        
        Args:
            tag_config: 点位配置，包含地址、数据类型等
            
        Returns:
            读取的数值，失败返回 None
        """
        if not self.is_connected:
            logger.warning("PLC 未连接")
            return None
        
        try:
            address = tag_config.get('address', '')
            data_type = tag_config.get('data_type', 'FLOAT')
            
            if self.plc_type == 's7':
                return self._read_s7_tag(address, data_type)
            elif self.plc_type == 'modbus':
                return self._read_modbus_tag(address, data_type)
            else:
                return None
                
        except Exception as e:
            logger.error(f"读取点位 {address} 失败：{e}")
            return None
    
    def _read_s7_tag(self, address: str, data_type: str) -> Optional[float]:
        """读取西门子 S7 点位"""
        # 解析地址，如 "MW100", "DB1.DBD4"
        if address.startswith('DB'):
            # DB 块地址
            parts = address.split('.')
            db_number = int(parts[0][2:])
            offset = int(parts[1][3:]) if 'D' in parts[1] else int(parts[1][1:])
            
            if data_type == 'FLOAT':
                data = self.client.db_read(db_number, offset, 4)
                return float.from_bytes(data, byteorder='big')
            elif data_type == 'INT':
                data = self.client.db_read(db_number, offset, 2)
                return int.from_bytes(data, byteorder='big')
            elif data_type == 'BOOL':
                bit_offset = int(address.split('.')[2]) if len(address.split('.')) > 2 else 0
                data = self.client.db_read(db_number, 0, 1)
                return bool(data[0] & (1 << bit_offset))
        
        elif address.startswith('M'):
            # M 存储区
            if 'W' in address:  # MW
                offset = int(address[1:].split('W')[1])
                if data_type == 'FLOAT':
                    data = self.client.read_area(snap7.types.Areas.MK, 0, offset, 4)
                    return float.from_bytes(data, byteorder='big')
                elif data_type == 'INT':
                    data = self.client.read_area(snap7.types.Areas.MK, 0, offset, 2)
                    return int.from_bytes(data, byteorder='big')
            elif 'X' in address:  # MX (位)
                byte_offset = int(address.split('X')[0][1:])
                bit_offset = int(address.split('X')[1])
                data = self.client.read_area(snap7.types.Areas.MK, 0, byte_offset, 1)
                return bool(data[0] & (1 << bit_offset))
        
        elif address.startswith('Q') or address.startswith('I'):
            # 输出/输入区
            area = snap7.types.Areas.PE if address.startswith('I') else snap7.types.Areas.PA
            if 'W' in address:
                offset = int(address[1:].split('W')[1])
                data = self.client.read_area(area, 0, offset, 4)
                return float.from_bytes(data, byteorder='big')
        
        logger.warning(f"不支持的 S7 地址格式：{address}")
        return None
    
    def _read_modbus_tag(self, address: str, data_type: str) -> Optional[float]:
        """读取 Modbus 点位"""
        try:
            # 解析地址，如 "40001" (保持寄存器)
            register_address = int(address) - 40001
            
            if data_type == 'FLOAT':
                result = self.client.read_holding_registers(register_address, 2, slave=1)
                if result.isError():
                    return None
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, 
                    byteorder=Endian.Big, 
                    wordorder=Endian.Big
                )
                return decoder.decode_32bit_float()
            
            elif data_type == 'INT':
                result = self.client.read_holding_registers(register_address, 1, slave=1)
                if result.isError():
                    return None
                return result.registers[0]
            
            elif data_type == 'BOOL':
                result = self.client.read_coils(register_address, 1, slave=1)
                if result.isError():
                    return None
                return result.bits[0]
            
            else:
                logger.warning(f"不支持的 Modbus 数据类型：{data_type}")
                return None
                
        except Exception as e:
            logger.error(f"Modbus 读取失败：{e}")
            return None
    
    def read_all_tags(self) -> Dict[str, Any]:
        """
        读取所有配置的点位
        
        Returns:
            数据字典 {tag_id: value}
        """
        data = {}
        
        for tag in self.tags:
            tag_id = tag.get('tag_id')
            value = self.read_tag(tag)
            
            if value is not None:
                data[tag_id] = {
                    'value': value,
                    'timestamp': datetime.now().isoformat(),
                    'quality': 'good'
                }
            else:
                data[tag_id] = {
                    'value': None,
                    'timestamp': datetime.now().isoformat(),
                    'quality': 'bad'
                }
        
        return data
    
    def start_continuous_collection(self, callback: Callable[[Dict[str, Any]], None]):
        """
        启动连续采集
        
        Args:
            callback: 数据回调函数，接收数据字典
        """
        if self._running.get():
            logger.warning("采集器已在运行")
            return
        
        self.callbacks.append(callback)
        self._running.set(True)
        self._reconnect_attempts.set(0)
        
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"连续采集已启动 (间隔：{self.scan_interval}秒)")
    
    def _collection_loop(self):
        """采集循环（带自动重连）"""
        import time
        
        while self._running.get():
            try:
                # 检查连接状态
                if not self._client_guard.is_connected:
                    if not self._try_reconnect():
                        time.sleep(self._reconnect_delay)
                        continue
                
                # 批量读取所有点位
                data = self.read_all_tags()
                
                # 重置重连计数
                self._reconnect_attempts.set(0)
                
                # 调用回调函数
                for callback in self.callbacks:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"回调函数执行失败：{e}")
                
                time.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"采集循环异常：{e}")
                self.disconnect()
                time.sleep(self._reconnect_delay)
    
    def _try_reconnect(self) -> bool:
        """尝试重连（带指数退避）"""
        attempts = self._reconnect_attempts.get()
        
        if attempts >= self._max_reconnect_attempts:
            logger.error(f"重连次数超过最大值 {self._max_reconnect_attempts}，放弃连接")
            self._reconnect_attempts.set(0)
            return False
        
        self._reconnect_attempts.set(attempts + 1)
        
        # 指数退避延迟
        delay = min(self._reconnect_delay * (2 ** attempts), 60)
        logger.info(f"尝试重连 {attempts + 1}/{self._max_reconnect_attempts}，{delay}s 后重试...")
        
        import time
        time.sleep(delay)
        
        return self.connect()
    
    def stop_continuous_collection(self):
        """停止连续采集"""
        self._running.set(False)
        if self._thread:
            self._thread.join(timeout=10)
        self.disconnect()
        logger.info("连续采集已停止")
    
    def reconnect(self):
        """重新连接 PLC"""
        self.disconnect()
        time.sleep(1)
        self.connect()


# 使用示例
if __name__ == "__main__":
    # 配置示例
    config = {
        'type': 's7',
        'host': '192.168.1.100',
        'port': 102,
        'rack': 0,
        'slot': 1,
        'scan_interval': 10,
        'tags': [
            {'tag_id': 'TAG_DO_001', 'address': 'MW100', 'data_type': 'FLOAT'},
            {'tag_id': 'TAG_PH_001', 'address': 'MW104', 'data_type': 'FLOAT'},
            {'tag_id': 'TAG_Pump_001', 'address': 'Q0.0', 'data_type': 'BOOL'}
        ]
    }
    
    collector = PLCCollector(config)
    
    # 连接并读取数据
    if collector.connect():
        data = collector.read_all_tags()
        print("采集到的数据:")
        for tag_id, info in data.items():
            print(f"  {tag_id}: {info['value']} ({info['quality']})")
        
        # 启动连续采集
        def on_data_received(data):
            print(f"\n[{datetime.now()}] 新数据到达:")
            for tag_id, info in data.items():
                print(f"  {tag_id}: {info['value']}")
        
        collector.start_continuous_collection(on_data_received)
        
        # 运行 30 秒后停止
        time.sleep(30)
        collector.stop_continuous_collection()
        collector.disconnect()
