# Miaota Industrial Agent - 用户手册

> **版本**: v1.0.0-beta1  
> **更新日期**: 2026-03-26

---

## 目录

1. [快速开始](#1-快速开始)
2. [系统概述](#2-系统概述)
3. [功能使用指南](#3-功能使用指南)
4. [常见问题](#4-常见问题)
5. [故障排除](#5-故障排除)

---

## 1. 快速开始

### 1.1 系统要求

| 资源 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 4核 | 8核+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 50GB SSD | 100GB+ SSD |
| 网络 | 100Mbps | 1000Mbps |
| Python | 3.9+ | 3.11+ |

### 1.2 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/miaota-industrial-agent.git
cd miaota-industrial-agent

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置系统
cp config/settings.yaml.example config/settings.yaml
# 编辑 config/settings.yaml 配置您的PLC参数

# 5. 启动服务
python src/main.py
```

### 1.3 Docker部署 (推荐)

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 查看状态
docker-compose ps
```

### 1.4 访问系统

- **Web界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **监控大屏**: http://localhost:8000/dashboard

---

## 2. 系统概述

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户层 (User Layer)                      │
│   Web界面    移动端      API客户端      大屏展示              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      应用层 (Application Layer)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │数据采集 │ │规则引擎 │ │异常检测 │ │LLM诊断 │            │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │时序预测 │ │告警管理 │ │报表导出 │ │知识库  │            │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      数据层 (Data Layer)                      │
│  InfluxDB    SQLite    ChromaDB    Redis                    │
│ (时序数据)   (关系数据) (向量数据)  (缓存)                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      设备层 (Device Layer)                    │
│         PLC S7          Modbus TCP          OPC UA          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心功能

#### 🔍 实时监控
- 实时数据曲线展示
- 设备状态概览
- 异常实时告警
- 历史数据查询

#### 🤖 智能诊断
- 自然语言故障描述
- AI根因分析
- 维修步骤建议
- 备件自动推荐

#### 📈 预测分析
- 设备趋势预测
- 异常提前预警
- 维护计划建议

#### 📚 知识库
- 技术文档管理
- 智能问答
- 历史案例检索

---

## 3. 功能使用指南

### 3.1 数据采集配置

#### 3.1.1 PLC连接配置

编辑 `config/settings.yaml`:

```yaml
plc:
  - name: "S7-1200-1"
    type: "s7"
    host: "192.168.1.10"
    port: 102
    rack: 0
    slot: 1
    
  - name: "Modbus-Device-1"
    type: "modbus"
    host: "192.168.1.20"
    port: 502
    unit_id: 1
```

#### 3.1.2 点位映射配置

创建 `config/tag_mapping.xlsx`:

| plc_address | tag_name | description | unit | min | max |
|-------------|----------|-------------|------|-----|-----|
| MW100 | DO_CONCENTRATION | 溶解氧浓度 | mg/L | 0 | 10 |
| MW102 | PH_VALUE | pH值 | - | 0 | 14 |
| MW104 | TEMPERATURE | 温度 | °C | 0 | 100 |

### 3.2 规则配置

#### 3.2.1 创建告警规则

通过Web界面或API:

```python
POST /api/rules
{
  "name": "缺氧异常",
  "type": "threshold",
  "tag": "DO_CONCENTRATION",
  "condition": {
    "operator": "<",
    "value": 2.0
  },
  "severity": "critical",
  "notification": {
    "channels": ["web", "feishu"],
    "message": "溶解氧浓度过低: {value} mg/L"
  }
}
```

#### 3.2.2 规则类型说明

| 规则类型 | 描述 | 使用场景 |
|----------|------|----------|
| threshold | 阈值规则 | 数值上下限检测 |
| duration | 持续异常 | 持续N秒异常触发 |
| rate | 变化率 | 变化速度过快/过慢 |
| composite | 组合规则 | 多条件逻辑组合 |
| correlation | 相关性 | 变量间关系异常 |

### 3.3 异常检测配置

#### 3.3.1 启用异常检测

```python
POST /api/anomaly/config
{
  "tag": "DO_CONCENTRATION",
  "algorithm": "isolation_forest",
  "params": {
    "contamination": 0.05,
    "window_size": 100
  },
  "auto_suppress": true
}
```

#### 3.3.2 检测算法选择

| 算法 | 适用场景 | 优势 |
|------|----------|------|
| 3sigma | 单变量、正态分布 | 简单、可解释 |
| IQR | 单变量、有异常值 | 鲁棒性强 |
| Isolation Forest | 多变量、高维 | 效果好、快速 |
| Mahalanobis | 多变量、相关性强 | 考虑相关性 |
| PCA | 多变量、降维 | 可视化友好 |

### 3.4 LLM诊断使用

#### 3.4.1 Web界面诊断

1. 访问 http://localhost:8000/diagnosis
2. 选择设备
3. 描述故障症状
4. 获取AI诊断结果

#### 3.4.2 API调用

```python
POST /api/diagnosis
{
  "device_id": "aeration_pool_1",
  "symptoms": "溶解氧浓度持续偏低，曝气风机运行正常，pH值在正常范围",
  "context": {
    "do_value": 1.2,
    "ph_value": 7.2,
    "blower_status": "running"
  }
}

# 响应
{
  "root_cause": "曝气盘部分堵塞",
  "confidence": 0.85,
  "possible_causes": [
    "曝气盘堵塞",
    "风机故障",
    "DO传感器漂移"
  ],
  "suggested_actions": [
    "检查并清洗曝气盘",
    "检查风机运行状态",
    "校准DO传感器"
  ],
  "spare_parts": [
    "曝气盘 × 5",
    "风机滤网 × 1"
  ]
}
```

### 3.5 知识库使用

#### 3.5.1 上传文档

```python
POST /api/knowledge/upload
Content-Type: multipart/form-data

file: 设备操作手册.pdf
category: "操作手册"
tags: ["曝气池", "维护"]
```

#### 3.5.2 知识问答

```python
POST /api/knowledge/query
{
  "question": "如何清洗曝气盘？",
  "top_k": 3
}
```

### 3.6 报表导出

#### 3.6.1 生成日报

```python
GET /api/reports/daily?date=2024-01-15&format=excel

# 返回: daily_report_2024-01-15.xlsx
```

#### 3.6.2 生成自定义报表

```python
POST /api/reports/custom
{
  "title": "月度运营报表",
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "metrics": ["进水量", "COD", "氨氮", "电耗"],
  "format": "pdf"
}
```

---

## 4. 常见问题

### Q1: 如何修改采集频率？

编辑 `config/settings.yaml`:

```yaml
collection:
  interval: 5  # 单位: 秒
  batch_size: 100
```

### Q2: 如何配置告警通知？

支持多种通知渠道:

```yaml
notification:
  channels:
    feishu:
      webhook_url: "https://open.feishu.cn/..."
    dingtalk:
      webhook_url: "https://oapi.dingtalk.com/..."
    sms:
      provider: "aliyun"
      access_key: "xxx"
```

### Q3: 如何备份数据？

```bash
# 备份InfluxDB
docker exec influxdb influx backup /backup

# 备份SQLite
cp data/db/miaota.db backup/miaota_$(date +%Y%m%d).db

# 备份配置
tar czvf backup/config_$(date +%Y%m%d).tar.gz config/
```

### Q4: 如何更新系统？

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取更新
git pull origin main

# 3. 更新依赖
pip install -r requirements.txt --upgrade

# 4. 重启服务
./scripts/restart.sh
```

### Q5: 如何添加新的PLC？

1. 编辑 `config/settings.yaml` 添加PLC配置
2. 更新 `config/tag_mapping.xlsx` 添加点位
3. 重启采集服务

---

## 5. 故障排除

### 5.1 无法连接PLC

**症状**: 数据采集状态显示"离线"

**排查步骤**:
1. 检查网络连通性: `ping <PLC_IP>`
2. 检查端口开放: `telnet <PLC_IP> <PORT>`
3. 检查PLC配置: 机架号、插槽号是否正确
4. 查看日志: `tail -f logs/collector.log`

### 5.2 告警不触发

**症状**: 规则已配置但告警未产生

**排查步骤**:
1. 检查规则状态: 是否启用
2. 检查数据流: 点位数据是否正常上报
3. 检查规则条件: 数值是否满足触发条件
4. 检查抑制策略: 是否在抑制期内

### 5.3 LLM诊断失败

**症状**: 诊断接口返回错误或超时

**排查步骤**:
1. 检查模型服务: 是否正常运行
2. 检查API密钥: 是否配置正确
3. 检查网络: 能否访问模型服务
4. 查看日志: `tail -f logs/diagnosis.log`

### 5.4 性能问题

**症状**: 系统响应慢

**优化建议**:
1. 增加内存: 建议16GB+
2. 启用缓存: 配置Redis缓存
3. 数据分区: 按时间分表
4. 查询优化: 添加索引

### 5.5 日志位置

| 模块 | 日志路径 |
|------|----------|
| 数据采集 | `logs/collector.log` |
| 规则引擎 | `logs/rule_engine.log` |
| 异常检测 | `logs/anomaly_detection.log` |
| LLM诊断 | `logs/diagnosis.log` |
| API服务 | `logs/api.log` |

### 5.6 联系支持

遇到问题无法解决？

- 📧 邮箱: support@miaota.ai
- 💬 社区: https://github.com/your-org/miaota-industrial-agent/discussions
- 🐛 问题反馈: https://github.com/your-org/miaota-industrial-agent/issues

---

## 附录

### A. API快速参考

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/data/realtime` | GET | 获取实时数据 |
| `/api/data/history` | GET | 查询历史数据 |
| `/api/alerts` | GET | 获取告警列表 |
| `/api/rules` | POST | 创建规则 |
| `/api/diagnosis` | POST | 执行诊断 |
| `/api/reports/export` | POST | 导出报表 |

### B. 配置文件模板

参见 `config/settings.yaml.example`

### C. 系统架构图

参见 `docs/architecture.md`

---

**文档版本**: v1.0.0-beta1  
**最后更新**: 2026-03-26
