# Miaota Industrial Agent - API 参考文档

> **版本**: v1.0.0-beta1  
> **Base URL**: `http://localhost:8000/api/v1`  
> **Content-Type**: `application/json`

---

## 目录

1. [认证](#1-认证)
2. [数据API](#2-数据api)
3. [告警API](#3-告警api)
4. [规则API](#4-规则api)
5. [诊断API](#5-诊断api)
6. [预测API](#6-预测api)
7. [知识库API](#7-知识库api)
8. [报表API](#8-报表api)
9. [系统API](#9-系统api)

---

## 1. 认证

### 1.1 登录

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

**响应**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_001",
    "username": "admin",
    "role": "admin"
  }
}
```

### 1.2 刷新Token

```http
POST /auth/refresh
Authorization: Bearer {access_token}
```

---

## 2. 数据API

### 2.1 获取实时数据

```http
GET /data/realtime?tags=DO_CONCENTRATION,PH_VALUE
```

**参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| tags | string | 是 | 点位标签，逗号分隔 |

**响应**:

```json
{
  "timestamp": "2024-01-15T08:30:00Z",
  "data": [
    {
      "tag": "DO_CONCENTRATION",
      "value": 3.5,
      "unit": "mg/L",
      "quality": "good",
      "timestamp": "2024-01-15T08:30:00Z"
    },
    {
      "tag": "PH_VALUE",
      "value": 7.2,
      "unit": "-",
      "quality": "good",
      "timestamp": "2024-01-15T08:30:00Z"
    }
  ]
}
```

### 2.2 查询历史数据

```http
GET /data/history?tag=DO_CONCENTRATION&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z&interval=1m
```

**参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| tag | string | 是 | 点位标签 |
| start | datetime | 是 | 开始时间 (ISO 8601) |
| end | datetime | 是 | 结束时间 (ISO 8601) |
| interval | string | 否 | 聚合间隔 (1s/1m/1h/1d) |
| aggregation | string | 否 | 聚合方式 (mean/max/min/sum) |

**响应**:

```json
{
  "tag": "DO_CONCENTRATION",
  "count": 1440,
  "interval": "1m",
  "data": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "value": 3.52,
      "min": 3.1,
      "max": 3.9,
      "count": 60
    }
  ]
}
```

### 2.3 获取点位列表

```http
GET /data/tags
```

**响应**:

```json
{
  "tags": [
    {
      "tag": "DO_CONCENTRATION",
      "description": "溶解氧浓度",
      "unit": "mg/L",
      "type": "float",
      "min": 0,
      "max": 10
    }
  ],
  "total": 25
}
```

---

## 3. 告警API

### 3.1 获取告警列表

```http
GET /alerts?status=active&severity=critical&limit=50
```

**参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| status | string | 否 | 状态 (active/resolved/acknowledged) |
| severity | string | 否 | 级别 (info/warning/critical/emergency) |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |
| limit | int | 否 | 返回数量 (默认50) |
| offset | int | 否 | 偏移量 |

**响应**:

```json
{
  "total": 156,
  "limit": 50,
  "offset": 0,
  "alerts": [
    {
      "alert_id": "ALT_001",
      "rule_id": "RULE_001",
      "rule_name": "缺氧异常",
      "severity": "critical",
      "status": "active",
      "message": "溶解氧浓度过低: 1.2 mg/L",
      "tag": "DO_CONCENTRATION",
      "value": 1.2,
      "threshold": 2.0,
      "triggered_at": "2024-01-15T08:30:00Z",
      "acknowledged_by": null,
      "acknowledged_at": null
    }
  ]
}
```

### 3.2 确认告警

```http
POST /alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "user": "张工",
  "comment": "已安排现场检查"
}
```

### 3.3 获取告警统计

```http
GET /alerts/statistics?period=24h
```

**响应**:

```json
{
  "period": "24h",
  "total_alerts": 45,
  "by_severity": {
    "critical": 5,
    "warning": 12,
    "info": 28
  },
  "by_status": {
    "active": 3,
    "acknowledged": 15,
    "resolved": 27
  },
  "mttr_minutes": 18.5
}
```

---

## 4. 规则API

### 4.1 获取规则列表

```http
GET /rules
```

**响应**:

```json
{
  "rules": [
    {
      "rule_id": "RULE_001",
      "name": "缺氧异常",
      "type": "threshold",
      "enabled": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-10T12:00:00Z"
    }
  ]
}
```

### 4.2 创建规则

```http
POST /rules
Content-Type: application/json

{
  "name": "pH值异常",
  "type": "threshold",
  "tag": "PH_VALUE",
  "condition": {
    "operator": ">",
    "value": 8.5
  },
  "severity": "warning",
  "notification": {
    "channels": ["web", "feishu"],
    "template": "pH值偏高: {value}"
  },
  "suppress_duration": 900
}
```

**规则类型**:

| 类型 | 描述 | condition示例 |
|------|------|---------------|
| threshold | 阈值 | `{"operator": ">", "value": 8.5}` |
| duration | 持续 | `{"operator": "<", "value": 2, "duration": 300}` |
| rate | 变化率 | `{"operator": ">", "value": 0.5, "window": 60}` |
| composite | 组合 | `{"operator": "AND", "rules": [...]}` |

### 4.3 更新规则

```http
PUT /rules/{rule_id}
Content-Type: application/json

{
  "enabled": false
}
```

### 4.4 删除规则

```http
DELETE /rules/{rule_id}
```

### 4.5 测试规则

```http
POST /rules/{rule_id}/test
Content-Type: application/json

{
  "value": 1.5
}
```

**响应**:

```json
{
  "triggered": true,
  "message": "条件满足，将触发告警",
  "severity": "critical"
}
```

---

## 5. 诊断API

### 5.1 执行诊断

```http
POST /diagnosis
Content-Type: application/json

{
  "device_id": "aeration_pool_1",
  "symptoms": "溶解氧浓度持续偏低，曝气风机运行正常",
  "context": {
    "do_value": 1.2,
    "ph_value": 7.2,
    "blower_status": "running"
  },
  "model": "qwen-turbo"
}
```

**响应**:

```json
{
  "diagnosis_id": "DIAG_001",
  "device_id": "aeration_pool_1",
  "symptoms": "溶解氧浓度持续偏低，曝气风机运行正常",
  "root_cause": "曝气盘部分堵塞",
  "confidence": 0.85,
  "reasoning": "根据症状和运行参数分析，风机运行正常排除风机故障，pH值正常排除生化异常，最可能原因是曝气盘堵塞导致曝气效率下降...",
  "possible_causes": [
    {"cause": "曝气盘堵塞", "probability": 0.85},
    {"cause": "风机故障", "probability": 0.10},
    {"cause": "DO传感器漂移", "probability": 0.05}
  ],
  "suggested_actions": [
    "检查并清洗曝气盘",
    "检查风机运行状态",
    "校准DO传感器"
  ],
  "spare_parts": [
    {"name": "曝气盘", "quantity": 5, "priority": "high"},
    {"name": "风机滤网", "quantity": 1, "priority": "medium"}
  ],
  "references": [
    {"title": "曝气系统维护手册", "type": "manual", "relevance": 0.92}
  ],
  "created_at": "2024-01-15T08:35:00Z"
}
```

### 5.2 获取诊断历史

```http
GET /diagnosis/history?device_id=aeration_pool_1&limit=10
```

### 5.3 生成诊断报告

```http
POST /diagnosis/{diagnosis_id}/report
Content-Type: application/json

{
  "format": "pdf",
  "include_charts": true
}
```

**响应**:

```json
{
  "report_id": "RPT_001",
  "download_url": "/api/reports/RPT_001.pdf",
  "expires_at": "2024-01-16T08:35:00Z"
}
```

---

## 6. 预测API

### 6.1 执行预测

```http
POST /forecast
Content-Type: application/json

{
  "tag": "DO_CONCENTRATION",
  "model": "prophet",
  "horizon": 24,
  "frequency": "1h"
}
```

**参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| tag | string | 是 | 点位标签 |
| model | string | 是 | 模型 (prophet/arima/lstm/neural_prophet) |
| horizon | int | 是 | 预测步数 |
| frequency | string | 是 | 频率 (1h/1d) |

**响应**:

```json
{
  "forecast_id": "FRC_001",
  "tag": "DO_CONCENTRATION",
  "model": "prophet",
  "predictions": [
    {
      "timestamp": "2024-01-16T00:00:00Z",
      "value": 3.52,
      "lower": 3.20,
      "upper": 3.84
    }
  ],
  "metrics": {
    "mae": 0.15,
    "rmse": 0.22,
    "mape": 4.2
  }
}
```

### 6.2 获取预测模型列表

```http
GET /forecast/models
```

### 6.3 评估预测模型

```http
POST /forecast/{model_id}/evaluate
Content-Type: application/json

{
  "test_period": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-07T00:00:00Z"
  }
}
```

---

## 7. 知识库API

### 7.1 上传文档

```http
POST /knowledge/documents
Content-Type: multipart/form-data

file: @设备手册.pdf
category: 操作手册
tags: 曝气池,维护
```

**响应**:

```json
{
  "document_id": "DOC_001",
  "filename": "设备手册.pdf",
  "status": "processing",
  "chunks": 25
}
```

### 7.2 查询知识库

```http
POST /knowledge/query
Content-Type: application/json

{
  "question": "如何清洗曝气盘？",
  "top_k": 3,
  "filter": {
    "category": "操作手册"
  }
}
```

**响应**:

```json
{
  "query": "如何清洗曝气盘？",
  "results": [
    {
      "document_id": "DOC_001",
      "title": "设备操作手册",
      "content": "曝气盘清洗步骤: 1. 关闭风机 2. 排空池内液体 3. 拆卸曝气盘...",
      "relevance_score": 0.92,
      "page": 15
    }
  ]
}
```

### 7.3 获取文档列表

```http
GET /knowledge/documents
```

### 7.4 删除文档

```http
DELETE /knowledge/documents/{document_id}
```

---

## 8. 报表API

### 8.1 生成日报

```http
GET /reports/daily?date=2024-01-15&format=excel
```

### 8.2 生成周报

```http
GET /reports/weekly?year=2024&week=3&format=pdf
```

### 8.3 生成自定义报表

```http
POST /reports/custom
Content-Type: application/json

{
  "title": "月度运营报表",
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "metrics": ["进水量", "COD", "氨氮", "电耗"],
  "format": "pdf",
  "include_charts": true
}
```

**响应**:

```json
{
  "report_id": "RPT_001",
  "download_url": "/api/reports/RPT_001.pdf",
  "file_size": 2456789,
  "created_at": "2024-01-15T08:35:00Z"
}
```

### 8.4 下载报表

```http
GET /reports/{report_id}/download
```

---

## 9. 系统API

### 9.1 获取系统状态

```http
GET /system/status
```

**响应**:

```json
{
  "status": "healthy",
  "version": "v1.0.0-beta1",
  "uptime": 86400,
  "components": {
    "collector": "running",
    "rule_engine": "running",
    "anomaly_detector": "running",
    "database": "connected"
  },
  "stats": {
    "tags_count": 125,
    "rules_count": 45,
    "active_alerts": 3
  }
}
```

### 9.2 获取系统指标

```http
GET /system/metrics
```

### 9.3 健康检查

```http
GET /health
```

**响应**:

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T08:35:00Z"
}
```

### 9.4 生成合规报告

```http
POST /system/compliance
Content-Type: application/json

{
  "standard": "等保2.0",
  "level": 3
}
```

---

## 错误码参考

| 错误码 | 描述 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或Token过期 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Validation Error | 数据验证失败 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

---

## 速率限制

- **默认限制**: 1000次/小时/IP
- **认证用户**: 10000次/小时/用户
- **限流响应**: `429 Too Many Requests`

---

## WebSocket 实时数据

连接地址: `ws://localhost:8000/ws/realtime`

### 订阅点位

```json
{
  "action": "subscribe",
  "tags": ["DO_CONCENTRATION", "PH_VALUE"]
}
```

### 接收数据

```json
{
  "type": "data",
  "timestamp": "2024-01-15T08:30:00Z",
  "data": {
    "DO_CONCENTRATION": 3.5,
    "PH_VALUE": 7.2
  }
}
```

---

**文档版本**: v1.0.0-beta1  
**最后更新**: 2026-03-26
