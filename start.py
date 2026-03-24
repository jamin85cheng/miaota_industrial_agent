#!/usr/bin/env python3
"""
Miaota Industrial Agent - 主启动脚本

用法:
    python start.py              # 启动完整系统
    python start.py --collect    # 仅数据采集
    python start.py --rules      # 仅规则引擎
    python start.py --demo       # 演示模式 (模拟数据)
"""

import sys
import time
import argparse
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core import TagMapper, RuleEngine
from src.data import PLCCollector


def setup_logging(log_level: str = "INFO"):
    """配置日志"""
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan> | {message}",
        level=log_level,
        colorize=True
    )
    
    # 文件输出
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}"
    )
    
    logger.info("日志系统初始化完成")


def main():
    parser = argparse.ArgumentParser(description='Miaota Industrial Agent 启动脚本')
    parser.add_argument('--collect', action='store_true', help='仅运行数据采集')
    parser.add_argument('--rules', action='store_true', help='仅运行规则引擎')
    parser.add_argument('--demo', action='store_true', help='演示模式 (使用模拟数据)')
    parser.add_argument('--config', type=str, default='config/settings.yaml', help='配置文件路径')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    logger.info("=" * 60)
    logger.info("🦞 Miaota Industrial Agent 启动中...")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        import yaml
        with open(args.config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"配置文件已加载：{args.config}")
        
        # 初始化点位映射
        tag_mapping_file = config.get('tag_mapping', {}).get('file', 'config/tag_mapping.xlsx')
        mapper = TagMapper(tag_mapping_file)
        logger.info(f"点位映射器已初始化：{len(mapper.tag_dict)} 个点位")
        
        # 初始化规则引擎
        rules_file = config.get('rules', {}).get('config_file', 'config/rules.json')
        rule_config = config.get('rules', {}).get('strategy', {})
        engine = RuleEngine(rules_file, config=rule_config)
        logger.info(f"规则引擎已初始化：{len(engine.rules)} 条规则")
        
        # 初始化数据采集
        plc_config = config.get('plc', {})
        if args.demo:
            plc_config['type'] = 'simulated'
            logger.info("演示模式：使用模拟数据")
        
        collector = PLCCollector(plc_config)
        logger.info(f"数据采集器已初始化：{plc_config.get('type', 's7')}@{plc_config.get('host', 'localhost')}")
        
        # 定义数据处理回调
        def process_data(data):
            """数据处理回调"""
            timestamp = data.get('timestamp', 'unknown')
            values = data.get('values', {})
            
            # 转换为 DataFrame
            import pandas as pd
            df = pd.DataFrame([values])
            
            # 执行规则评估
            alerts = engine.evaluate(df)
            
            # 输出结果
            if alerts:
                logger.warning(f"检测到 {len(alerts)} 个异常:")
                for alert in alerts:
                    logger.warning(f"  ⚠️  [{alert['severity'].upper()}] {alert['name']}")
                    logger.warning(f"     标签：{alert['label']}")
                    if alert.get('suggested_actions'):
                        logger.warning(f"     建议：{alert['suggested_actions'][0]}")
            else:
                logger.debug(f"{timestamp} - 系统运行正常")
        
        # 注册回调
        collector.register_callback(process_data)
        
        # 启动采集
        if args.collect or args.rules:
            # 仅采集或仅规则测试
            addresses = {tag_id: info['plc_address'] for tag_id, info in mapper.tag_dict.items()}
            collector.start_collection(addresses)
            
            logger.info("数据采集已启动，按 Ctrl+C 停止...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("用户中断，正在停止...")
            finally:
                collector.stop_collection()
                collector.disconnect()
        else:
            # 完整模式
            addresses = {tag_id: info['plc_address'] for tag_id, info in mapper.tag_dict.items()}
            collector.start_collection(addresses)
            
            logger.info("系统已完全启动，按 Ctrl+C 停止...")
            logger.info("监控大屏地址：http://localhost:8501 (如已启动 Streamlit)")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("用户中断，正在停止...")
            finally:
                collector.stop_collection()
                collector.disconnect()
        
        logger.info("系统已安全停止")
        
    except Exception as e:
        logger.error(f"启动失败：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
