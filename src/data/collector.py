"""
PLC 数据采集器
支持西门子 S7、Modbus TCP 等协议
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from loguru import logger
import pandas as pd

# 尝试导入 PLC 库，如果未安装则使用模拟模式
try:
    import snap7
    from snap7.util import *
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    logger.warning("python-snap7 未安装，使用模拟数据模式")

try:
    from pymodbus.client import ModbusTcpClient
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    logger.warning("pymodbus 未安装，Modbus 功能不可用")


class PLCCollector:
    """PLC 数据采集器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器
        
        Args:
            config: 配置字典，包含 PLC 连接参数
        """
        self.config = config
        self.plc_type = config.get('type', 's7')
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 102)
        
        # 采集控制
        self.scan_interval = config.get('scan_interval', 10)  # 秒
        self.running = False
        self.collection_thread: Optional[threading.Thread] = None
        
        # 数据回调
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # 最新数据缓存
        self.latest_data: Dict[str, Any] = {}
        self.data_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # 连接状态
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 5)
        
        # 初始化 PLC 客户端
        self._init_plc_client()
        
        logger.info(f"PLCCollector 初始化完成：{self.plc_type}@{self.host}:{self.port}")
    
    def _init_plc_client(self):
        """初始化 PLC 客户端"""
        if self.plc_type == 's7':
            if SNAP7_AVAILABLE:
                self.client = snap7.client.Client()
            else:
                self.client = None
                logger.info("S7 客户端将使用模拟模式")
        
        elif self.plc_type == 'modbus':
            if PYMODBUS_AVAILABLE:
                self.client = ModbusTcpClient(self.host, port=self.port)
            else:
                self.client = None
                logger.info("Modbus 客户端将使用模拟模式")
        
        else:
            raise ValueError(f"不支持的 PLC 类型：{self.plc_type}")
    
    def connect(self) -> bool:
        """连接到 PLC"""
        try:
            if self.plc_type == 's7':
                if self.client:
                    rack = self.config.get('rack', 0)
                    slot = self.config.get('slot', 1)
                    self.client.connect(self.host, rack, slot, self.port)
                    self.connected = self.client.get_connected()
                else:
                    # 模拟模式
                    logger.info("模拟模式：连接到虚拟 PLC")
                    self.connected = True
            
            elif self.plc_type == 'modbus':
                if self.client:
                    self.connected = self.client.connect()
                else:
                    logger.info("模拟模式：连接到虚拟 Modbus")
                    self.connected = True
            
            if self.connected:
                logger.info(f"成功连接到 PLC {self.host}:{self.port}")
                self.reconnect_attempts = 0
            else:
                logger.warning(f"连接 PLC 失败")
            
            return self.connected
            
        except Exception as e:
            logger.error(f"连接 PLC 异常：{e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.plc_type == 's7' and self.client:
                self.client.disconnect()
            elif self.plc_type == 'modbus' and self.client:
                self.client.close()
            
            self.connected = False
            logger.info("已断开 PLC 连接")
        except Exception as e:
            logger.error(f"断开连接异常：{e}")
    
    def read_data(self, addresses: Dict[str, str]) -> Dict[str, Any]:
        """
        读取 PLC 数据
        
        Args:
            addresses: 点位地址映射 {tag_id: plc_address}
                      例如：{"TAG_DO_001": "MW100", "TAG_Pump_001": "Q0.0"}
        
        Returns:
            读取的数据字典 {tag_id: value}
        """
        if not self.connected:
            if not self.connect():
                return {}
        
        data = {}
        
        try:
            if self.plc_type == 's7':
                data = self._read_s7(addresses)
            elif self.plc_type == 'modbus':
                data = self._read_modbus(addresses)
            else:
                data = self._read_simulated(addresses)
            
            # 更新缓存
            timestamp = datetime.now().isoformat()
            self.latest_data = {
                'timestamp': timestamp,
                'values': data
            }
            
            # 保存到历史
            self.data_history.append(self.latest_data)
            if len(self.data_history) > self.max_history_size:
                self.data_history.pop(0)
            
            # 触发回调
            for callback in self.data_callbacks:
                try:
                    callback(self.latest_data)
                except Exception as e:
                    logger.error(f"数据回调执行失败：{e}")
            
            return data
            
        except Exception as e:
            logger.error(f"读取 PLC 数据异常：{e}")
            self.connected = False
            return {}
    
    def _read_s7(self, addresses: Dict[str, str]) -> Dict[str, Any]:
        """读取西门子 S7 PLC 数据"""
        if not self.client:
            return self._read_simulated(addresses)
        
        data = {}
        
        for tag_id, address in addresses.items():
            try:
                # 解析地址类型
                if address.startswith('MW'):
                    # 字寄存器 (16 位整数)
                    db_number = 0
                    offset = int(address[2:])
                    value = self.client.db_read(db_number, offset, 2)
                    data[tag_id] = int.from_bytes(value, byteorder='big', signed=True)
                
                elif address.startswith('MD'):
                    # 双字寄存器 (32 位浮点数)
                    db_number = 0
                    offset = int(address[2:])
                    value = self.client.db_read(db_number, offset, 4)
                    data[tag_id] = float.from_bytes(value, byteorder='big')
                
                elif address.startswith('Q') or address.startswith('I'):
                    # 输入/输出位
                    # 简化处理，实际需要根据具体地址解析
                    data[tag_id] = False  # 占位符
                
                else:
                    logger.warning(f"未知地址格式：{address}")
                    data[tag_id] = None
                    
            except Exception as e:
                logger.error(f"读取地址 {address} 失败：{e}")
                data[tag_id] = None
        
        return data
    
    def _read_modbus(self, addresses: Dict[str, str]) -> Dict[str, Any]:
        """读取 Modbus PLC 数据"""
        if not self.client:
            return self._read_simulated(addresses)
        
        data = {}
        
        for tag_id, address in addresses.items():
            try:
                # 假设地址为保持寄存器 (4xxxx)
                register_addr = int(address)
                result = self.client.read_holding_registers(register_addr, 1, slave=1)
                
                if not result.isError():
                    data[tag_id] = result.registers[0]
                else:
                    data[tag_id] = None
                    
            except Exception as e:
                logger.error(f"读取 Modbus 地址 {address} 失败：{e}")
                data[tag_id] = None
        
        return data
    
    def _read_simulated(self, addresses: Dict[str, str]) -> Dict[str, Any]:
        """生成模拟数据 (用于测试)"""
        import random
        
        data = {}
        for tag_id, address in addresses.items():
            # 根据 tag_id 生成有意义的模拟数据
            if 'DO' in tag_id:
                # 溶解氧：2.0-8.0 之间波动
                data[tag_id] = round(random.uniform(2.0, 8.0), 2)
            elif 'PH' in tag_id:
                # pH 值：6.5-8.5 之间波动
                data[tag_id] = round(random.uniform(6.5, 8.5), 2)
            elif 'COD' in tag_id:
                # COD: 50-120 之间波动
                data[tag_id] = round(random.uniform(50, 120), 1)
            elif 'Pump' in tag_id and 'Status' in tag_id:
                # 泵状态：90% 概率运行
                data[tag_id] = random.random() > 0.1
            elif 'Flow' in tag_id:
                # 流量：100-150 之间波动
                data[tag_id] = round(random.uniform(100, 150), 1)
            elif 'Temp' in tag_id:
                # 温度：20-35 之间波动
                data[tag_id] = round(random.uniform(20, 35), 1)
            elif 'Pressure' in tag_id:
                # 压力：0.3-0.7 之间波动
                data[tag_id] = round(random.uniform(0.3, 0.7), 2)
            else:
                # 默认随机值
                data[tag_id] = round(random.uniform(0, 100), 2)
        
        return data
    
    def start_collection(self, addresses: Dict[str, str]):
        """启动连续采集"""
        if self.running:
            logger.warning("采集已在运行中")
            return
        
        self.running = True
        self.addresses = addresses
        
        def collection_loop():
            logger.info("开始连续数据采集...")
            while self.running:
                start_time = time.time()
                
                # 读取数据
                data = self.read_data(addresses)
                
                # 计算耗时
                elapsed = time.time() - start_time
                sleep_time = max(0, self.scan_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            logger.info("数据采集已停止")
        
        self.collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self.collection_thread.start()
    
    def stop_collection(self):
        """停止连续采集"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
            self.collection_thread = None
        logger.info("数据采集已停止")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注册数据回调函数"""
        self.data_callbacks.append(callback)
        logger.info(f"注册数据回调，当前共 {len(self.data_callbacks)} 个回调")
    
    def get_latest_data(self) -> Dict[str, Any]:
        """获取最新数据"""
        return self.latest_data
    
    def get_historical_data(self, minutes: int = 60) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            minutes: 获取最近多少分钟的数据
            
        Returns:
            DataFrame，索引为时间，列为各点位值
        """
        if not self.data_history:
            return pd.DataFrame()
        
        # 转换为 DataFrame
        records = []
        for record in self.data_history:
            row = {'timestamp': record['timestamp']}
            row.update(record.get('values', {}))
            records.append(row)
        
        df = pd.DataFrame(records)
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
        
        # 返回指定时间范围的数据
        cutoff_idx = max(0, len(df) - int(minutes * 60 / self.scan_interval))
        return df.iloc[cutoff_idx:]
    
    def __del__(self):
        """析构函数"""
        self.stop_collection()
        self.disconnect()


# 使用示例
if __name__ == "__main__":
    # 配置
    config = {
        'type': 's7',
        'host': '192.168.1.100',
        'port': 102,
        'rack': 0,
        'slot': 1,
        'scan_interval': 5
    }
    
    # 定义要采集的地址
    addresses = {
        'TAG_DO_001': 'MD100',
        'TAG_PH_001': 'MD104',
        'TAG_COD_001': 'MD108',
        'TAG_Pump_001_Status': 'Q0.0',
        'TAG_Flow_001': 'MD112'
    }
    
    # 创建采集器
    collector = PLCCollector(config)
    
    # 定义回调函数
    def on_data_received(data):
        print(f"\n收到数据 @ {data['timestamp']}:")
        for tag, value in data['values'].items():
            print(f"  {tag}: {value}")
    
    collector.register_callback(on_data_received)
    
    # 启动采集
    try:
        collector.start_collection(addresses)
        print("采集已启动，按 Ctrl+C 停止...")
        
        # 运行 60 秒
        time.sleep(60)
        
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        collector.stop_collection()
        collector.disconnect()
