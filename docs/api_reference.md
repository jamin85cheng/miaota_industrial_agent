# API 参考文档

**版本**: v1.0.0-beta2 (MiroFish)

**基础URL**: `http://localhost:8000`

---

## 🔐 认证

所有API（除了健康检查）都需要认证。

### 方式1: Bearer Token
```
Authorization: Bearer <your_access_token>
```

### 方式2: API Key
```
X-API-Key: <your_api_key>
```

---

## 📋 API 端点概览

### V1 API (基础功能)
| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /devices` | 设备列表 |
| `POST /devices` | 创建设备 |
| `GET /collection/status` | 采集状态 |
| `POST /collection/data/query` | 数据查询 |
| `GET /alerts` | 告警列表 |
| `POST /analysis/anomaly` | 异常检测 |
| `POST /knowledge/search` | 知识搜索 |

### V2 API (新增 - MiroFish集成)
| 端点 | 说明 |
|------|------|
| `POST /v2/diagnosis/analyze` | 多智能体诊断 |
| `GET /v2/diagnosis/task/{id}` | 任务状态查询 |
| `POST /v2/diagnosis/knowledge/query` | GraphRAG查询 |
| `GET /v2/diagnosis/knowledge/graph` | 知识图谱 |
| `GET /v2/diagnosis/experts` | 专家列表 |
| `GET /v2/diagnosis/society/status` | CAMEL社会状态 |

---

## 🔥 V2 API 详解

### 多智能体诊断

#### POST /v2/diagnosis/analyze

执行多智能体协同诊断。

**请求体**:
```json
{
  "symptoms": "曝气池溶解氧持续偏低，风机噪音异常",
  "device_id": "DEV_001",
  "sensor_data": {
    "temperature": 45.2,
    "pressure": 5.8,
    "vibration": 8.5,
    "current": 25.3
  },
  "use_multi_agent": true,
  "use_graph_rag": true,
  "use_camel": false,
  "priority": "high"
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symptoms | string | 是 | 故障症状描述 |
| device_id | string | 否 | 相关设备ID |
| sensor_data | object | 否 | 传感器数据 |
| use_multi_agent | boolean | 否 | 使用多智能体诊断 |
| use_graph_rag | boolean | 否 | 使用知识图谱增强 |
| use_camel | boolean | 否 | 使用CAMEL社会协作 |
| priority | string | 否 | 优先级: critical/high/normal/low |

**响应** (同步模式):
```json
{
  "diagnosis_id": "MAD_ABC123DEF456",
  "status": "completed",
  "message": "多智能体诊断完成",
  "result": {
    "diagnosis_id": "MAD_ABC123DEF456",
    "symptoms": "曝气池溶解氧持续偏低，风机噪音异常",
    "final_conclusion": "曝气盘部分堵塞，导致曝气效率下降40%",
    "confidence": 0.85,
    "consensus_level": 0.8,
    "expert_opinions": [
      {
        "expert_type": "mechanical",
        "expert_name": "机械故障诊断专家",
        "confidence": 0.82,
        "root_cause": "曝气盘部分堵塞，导致曝气效率下降40%",
        "evidence": [
          "振动频谱分析显示异常峰值",
          "温度梯度变化符合机械磨损模式"
        ],
        "suggestions": [
          "检查并清洗曝气盘",
          "检查风机叶轮是否平衡"
        ],
        "reasoning": "通过振动频谱分析，发现..."
      },
      {
        "expert_type": "electrical",
        "expert_name": "电气系统专家",
        "confidence": 0.75,
        "root_cause": "电机绝缘老化，电流不平衡度超过15%",
        ...
      }
    ],
    "dissenting_views": [],
    "recommended_actions": [
      {
        "action": "清洗曝气盘",
        "priority": "critical",
        "estimated_time": "2-4小时",
        "requires_shutdown": true
      }
    ],
    "spare_parts": [
      {
        "name": "微孔曝气盘",
        "spec": "Φ215mm",
        "quantity": 5
      }
    ],
    "simulation_scenarios": [
      {
        "scenario": "及时处理",
        "outcome": "预计4小时内恢复正常",
        "risk_level": "low"
      }
    ]
  }
}
```

**响应** (异步模式 - use_camel=true):
```json
{
  "diagnosis_id": "TASK_XYZ789",
  "status": "processing",
  "message": "CAMEL协作诊断已启动，请查询任务状态获取结果",
  "task_id": "TASK_XYZ789"
}
```

---

#### GET /v2/diagnosis/task/{task_id}

查询诊断任务状态（用于异步诊断）。

**响应**:
```json
{
  "task_id": "TASK_XYZ789",
  "status": "completed",
  "progress": {
    "current_step": 5,
    "total_steps": 5,
    "current_action": "诊断完成",
    "percentage": 100,
    "estimated_remaining_seconds": null
  },
  "result": { ... },
  "error": null,
  "duration_seconds": 12.5
}
```

---

### GraphRAG 知识图谱

#### POST /v2/diagnosis/knowledge/query

使用GraphRAG查询工业知识。

**请求体**:
```json
{
  "query": "轴承过热的原因和解决方案"
}
```

**响应**:
```json
{
  "query": "轴承过热的原因和解决方案",
  "retrieved_context": [
    {
      "type": "subgraph",
      "entity": {
        "id": "FAULT_002",
        "name": "轴承过热",
        "entity_type": "fault",
        "description": "轴承温度超过正常范围"
      },
      "subgraph": {
        "nodes": [...],
        "edges": [...]
      },
      "relevance_score": 0.95
    }
  ],
  "answer": "根据知识图谱分析，轴承过热涉及...",
  "sources": ["FAULT_002", "CAUSE_002", "SOL_002"]
}
```

---

#### GET /v2/diagnosis/knowledge/graph

获取知识图谱数据。

**查询参数**:
- `entity_id`: 可选，指定中心实体
- `depth`: 可选，子图深度（默认2）

**响应** (子图查询):
```json
{
  "nodes": [
    {
      "id": "DEV_001",
      "name": "曝气机",
      "entity_type": "device",
      "attributes": {"type": "离心风机", "power": "15kW"},
      "description": "污水处理曝气设备"
    },
    {
      "id": "FAULT_001",
      "name": "曝气不足",
      "entity_type": "fault",
      ...
    }
  ],
  "edges": [
    {
      "source": "DEV_001",
      "target": "FAULT_001",
      "relation": "manifests_as"
    }
  ]
}
```

---

### 专家与CAMEL社会

#### GET /v2/diagnosis/experts

获取可用的专家Agent列表。

**响应**:
```json
{
  "total": 5,
  "experts": [
    {
      "id": "EXP_MECH",
      "name": "机械故障诊断专家",
      "type": "mechanical",
      "capabilities": ["振动分析", "轴承诊断", "动平衡"],
      "description": "精通旋转机械故障诊断"
    },
    {
      "id": "EXP_ELEC",
      "name": "电气系统专家",
      "type": "electrical",
      "capabilities": ["电机诊断", "绝缘测试", "变频控制"],
      "description": "精通电气系统诊断"
    },
    {
      "id": "EXP_PROC",
      "name": "工艺分析专家",
      "type": "process",
      "capabilities": ["工艺优化", "参数调节", "水质分析"],
      "description": "精通污水处理工艺"
    },
    {
      "id": "EXP_SENSOR",
      "name": "传感器专家",
      "type": "sensor",
      "capabilities": ["仪表校准", "漂移诊断", "信号分析"],
      "description": "精通工业仪表诊断"
    },
    {
      "id": "EXP_HIST",
      "name": "历史案例专家",
      "type": "historical",
      "capabilities": ["案例匹配", "模式识别", "知识推理"],
      "description": "基于历史案例推理"
    }
  ]
}
```

---

#### GET /v2/diagnosis/society/status

获取CAMEL社会运行状态。

**响应**:
```json
{
  "society_id": "industrial_diagnosis_001",
  "name": "工业故障诊断专家委员会",
  "agent_count": 5,
  "task_count": 12,
  "active_tasks": 3,
  "agents": [
    {
      "agent_id": "EXP_MECH_001",
      "name": "机械专家",
      "role": "expert",
      "capabilities": ["振动分析", "轴承诊断"],
      "is_busy": false,
      "task_count": 5
    }
  ],
  "recent_messages": 128
}
```

---

## 🔧 V1 API 参考

### 设备管理

#### GET /devices

获取设备列表。

**查询参数**:
- `type`: 设备类型过滤 (s7|modbus)
- `status`: 状态过滤 (online|offline|error)
- `skip`: 分页起始 (默认0)
- `limit`: 每页数量 (默认100, 最大1000)

**响应**:
```json
{
  "total": 18,
  "devices": [
    {
      "id": "DEV_001",
      "name": "PLC-001",
      "type": "s7",
      "host": "192.168.1.10",
      "port": 102,
      "status": "online",
      "last_seen": "2024-01-15T10:30:00Z",
      "tag_count": 24,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### 数据采集

#### POST /collection/data/query

查询历史数据。

**请求体**:
```json
{
  "tags": ["temperature", "pressure"],
  "start_time": "2024-01-15T00:00:00Z",
  "end_time": "2024-01-15T23:59:59Z",
  "aggregation": "mean",
  "interval": "1h"
}
```

---

## 📊 错误处理

### 错误响应格式
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "field": "symptoms",
      "issue": "字段必填"
    }
  }
}
```

### 状态码
| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 验证错误 |
| 500 | 服务器内部错误 |

---

## 💡 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_access_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# V2 多智能体诊断
response = requests.post(
    f"{BASE_URL}/v2/diagnosis/analyze",
    headers=headers,
    json={
        "symptoms": "曝气池溶解氧持续偏低",
        "sensor_data": {"do": 1.5, "vibration": 8.5},
        "use_multi_agent": True,
        "use_graph_rag": True
    }
)

result = response.json()
print(f"诊断结论: {result['result']['final_conclusion']}")
print(f"置信度: {result['result']['confidence']}")

# 查询任务状态（异步诊断）
task_id = result.get("task_id")
if task_id:
    status = requests.get(
        f"{BASE_URL}/v2/diagnosis/task/{task_id}",
        headers=headers
    ).json()
    print(f"任务状态: {status['status']}")
    print(f"进度: {status['progress']['percentage']}%")
```

### JavaScript 示例

```javascript
// V2 多智能体诊断
const diagnose = async (symptoms, sensorData) => {
  const response = await fetch('http://localhost:8000/v2/diagnosis/analyze', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      symptoms,
      sensor_data: sensorData,
      use_multi_agent: true,
      use_graph_rag: true
    })
  });
  
  return await response.json();
};

// 使用
diagnose("曝气池DO偏低", {do: 1.5, vibration: 8.5})
  .then(result => {
    console.log('诊断结论:', result.result.final_conclusion);
    console.log('置信度:', result.result.confidence);
    console.log('专家建议:', result.result.recommended_actions);
  });
```

---

## 📚 相关文档

- [CHANGELOG.md](../CHANGELOG.md) - 版本更新日志
- [README.md](../README.md) - 项目说明
- [用户手册](user_manual.md) - 详细使用指南

---

## 🙏 致谢

本API基于以下开源项目构建：

- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [Pydantic](https://docs.pydantic.dev/) - 数据验证
- [MiroFish](https://github.com/666ghj/MiroFish) - 群体智能引擎灵感
- [CAMEL-AI](https://www.camel-ai.org/) - 多智能体框架

---

**版本**: v1.0.0-beta2 (MiroFish) | **更新时间**: 2026-03-27
