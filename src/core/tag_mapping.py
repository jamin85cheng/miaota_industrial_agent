"""
点位语义化映射模块
将 PLC 寄存器地址转换为业务含义
"""

import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger
from pathlib import Path


class TagMapper:
    """PLC 点位语义化映射器"""
    
    def __init__(self, mapping_file: str):
        """
        初始化映射器
        
        Args:
            mapping_file: Excel 映射表路径
        """
        self.mapping_file = Path(mapping_file)
        self.mapping_df: Optional[pd.DataFrame] = None
        self.tag_dict: Dict[str, Dict[str, Any]] = {}
        
        self.load_mapping()
        logger.info(f"TagMapper 初始化完成，加载 {len(self.tag_dict)} 个点位")
    
    def load_mapping(self):
        """加载映射表"""
        if not self.mapping_file.exists():
            logger.warning(f"映射文件不存在：{self.mapping_file}，创建空映射")
            self._create_template()
            return
        
        try:
            self.mapping_df = pd.read_excel(self.mapping_file)
            
            # 构建字典：点位 ID → 完整信息
            for _, row in self.mapping_df.iterrows():
                tag_id = row.get('点位 ID')
                if pd.isna(tag_id):
                    continue
                
                self.tag_dict[tag_id] = {
                    'plc_address': row.get('PLC 地址', ''),
                    'device_name': row.get('设备名称', ''),
                    'business_meaning': row.get('业务含义', ''),
                    'data_type': row.get('数据类型', 'FLOAT'),
                    'unit': row.get('单位', ''),
                    'range_min': row.get('量程范围', '').split('-')[0] if '-' in str(row.get('量程范围', '')) else None,
                    'range_max': row.get('量程范围', '').split('-')[1] if '-' in str(row.get('量程范围', '')) else None,
                    'normal_min': row.get('正常阈值', '').split('-')[0] if '-' in str(row.get('正常阈值', '')) else None,
                    'normal_max': row.get('正常阈值', '').split('-')[1] if '-' in str(row.get('正常阈值', '')) else None,
                    'alarm_min': row.get('报警阈值', ''),
                    'alarm_max': row.get('报警阈值', ''),
                    'scan_interval': row.get('采集频率', 10),
                    'related_tags': row.get('关联标签', [])
                }
            
            logger.info(f"成功加载 {len(self.tag_dict)} 个点位映射")
            
        except Exception as e:
            logger.error(f"加载映射表失败：{e}")
            raise
    
    def _create_template(self):
        """创建映射表模板"""
        template_data = {
            '点位 ID': ['TAG_DO_001', 'TAG_PH_001', 'TAG_Pump_001_Status'],
            'PLC 地址': ['MW100', 'MW104', 'Q0.0'],
            '设备名称': ['1#曝气池', '1#曝气池', '1#提升泵'],
            '业务含义': ['溶解氧浓度', 'pH 值', '运行状态'],
            '数据类型': ['FLOAT', 'FLOAT', 'BOOL'],
            '单位': ['mg/L', '', ''],
            '量程范围': ['0-20', '0-14', ''],
            '正常阈值': ['2.0-8.0', '6.5-8.5', ''],
            '报警阈值': ['<1.5 或 >10.0', '<6.0 或 >9.0', ''],
            '采集频率': [10, 10, 5],
            '关联标签': ['TAG_AirFlow_001', '', 'TAG_Flow_001'],
            '备注': ['需温度补偿', '', '']
        }
        
        df = pd.DataFrame(template_data)
        
        # 确保目录存在
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(self.mapping_file, index=False)
        logger.info(f"已创建映射表模板：{self.mapping_file}")
    
    def translate(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将原始 PLC 数据转换为语义化数据
        
        Args:
            raw_data: {"MW100": 3.5, "Q0.0": True, ...}
            
        Returns:
            {"曝气池溶解氧_DO": 3.5, "1#提升泵_状态": True, ...}
        """
        semantic_data = {}
        
        # 反向映射：PLC 地址 → 点位 ID
        address_to_tag = {v['plc_address']: k for k, v in self.tag_dict.items()}
        
        for plc_address, value in raw_data.items():
            tag_id = address_to_tag.get(plc_address)
            if tag_id:
                tag_info = self.tag_dict[tag_id]
                # 使用业务含义作为键名
                key = f"{tag_info['device_name']}_{tag_info['business_meaning']}"
                semantic_data[key] = {
                    'value': value,
                    'unit': tag_info['unit'],
                    'tag_id': tag_id,
                    'plc_address': plc_address
                }
        
        return semantic_data
    
    def get_tag_info(self, tag_id: str) -> Optional[Dict[str, Any]]:
        """获取点位详细信息"""
        return self.tag_dict.get(tag_id)
    
    def get_tags_by_device(self, device_name: str) -> Dict[str, Dict[str, Any]]:
        """获取某设备的所有点位"""
        return {
            k: v for k, v in self.tag_dict.items()
            if v.get('device_name') == device_name
        }
    
    def get_tags_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        按类别获取点位
        类别可以是：water_treatment, waste_gas, equipment 等
        """
        # 这里可以根据实际需求扩展分类逻辑
        return self.tag_dict
    
    def validate_value(self, tag_id: str, value: float) -> Dict[str, Any]:
        """
        验证点位值是否在正常范围内
        
        Returns:
            {
                'is_valid': bool,
                'status': 'normal' | 'warning' | 'alarm',
                'message': str
            }
        """
        tag_info = self.get_tag_info(tag_id)
        if not tag_info:
            return {'is_valid': True, 'status': 'unknown', 'message': '点位不存在'}
        
        # 检查量程
        range_min = tag_info.get('range_min')
        range_max = tag_info.get('range_max')
        if range_min and float(value) < float(range_min):
            return {
                'is_valid': False,
                'status': 'alarm',
                'message': f"值 {value} 低于量程下限 {range_min}"
            }
        if range_max and float(value) > float(range_max):
            return {
                'is_valid': False,
                'status': 'alarm',
                'message': f"值 {value} 高于量程上限 {range_max}"
            }
        
        # 检查正常范围
        normal_min = tag_info.get('normal_min')
        normal_max = tag_info.get('normal_max')
        if normal_min and float(value) < float(normal_min):
            return {
                'is_valid': True,
                'status': 'warning',
                'message': f"值 {value} 低于正常范围 {normal_min}-{normal_max}"
            }
        if normal_max and float(value) > float(normal_max):
            return {
                'is_valid': True,
                'status': 'warning',
                'message': f"值 {value} 高于正常范围 {normal_min}-{normal_max}"
            }
        
        return {
            'is_valid': True,
            'status': 'normal',
            'message': '数值正常'
        }
    
    def reload(self):
        """重新加载映射表 (支持热更新)"""
        logger.info("重新加载点位映射表...")
        self.tag_dict.clear()
        self.load_mapping()


# 使用示例
if __name__ == "__main__":
    mapper = TagMapper('config/tag_mapping.xlsx')
    
    # 模拟原始 PLC 数据
    raw_plc_data = {
        'MW100': 3.5,
        'MW104': 7.2,
        'Q0.0': True
    }
    
    # 转换为语义化数据
    semantic_data = mapper.translate(raw_plc_data)
    print("语义化数据:")
    for key, info in semantic_data.items():
        print(f"  {key}: {info['value']} {info['unit']}")
    
    # 验证数值
    validation = mapper.validate_value('TAG_DO_001', 1.2)
    print(f"\n验证结果：{validation}")
