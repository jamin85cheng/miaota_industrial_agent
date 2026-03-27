# Miaota Industrial Agent - 开发指南

> **版本**: v1.0.0-beta1  
> **更新日期**: 2026-03-26

---

## 目录

1. [开发环境搭建](#1-开发环境搭建)
2. [项目结构](#2-项目结构)
3. [代码规范](#3-代码规范)
4. [测试指南](#4-测试指南)
5. [贡献指南](#5-贡献指南)
6. [架构设计](#6-架构设计)

---

## 1. 开发环境搭建

### 1.1 前置要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 开发语言 |
| Git | 2.30+ | 版本控制 |
| Docker | 20.10+ | 容器化 |
| VSCode | Latest | 推荐IDE |

### 1.2 环境配置

#### 步骤1: 克隆仓库

```bash
git clone https://github.com/your-org/miaota-industrial-agent.git
cd miaota-industrial-agent
```

#### 步骤2: 创建虚拟环境

```bash
# 使用venv
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: venv\Scripts\activate  # Windows

# 或使用conda
conda create -n miaota python=3.11
conda activate miaota
```

#### 步骤3: 安装依赖

```bash
# 开发依赖
pip install -r requirements-dev.txt

# 生产依赖
pip install -r requirements.txt
```

#### 步骤4: 安装pre-commit钩子

```bash
pre-commit install
```

#### 步骤5: 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 1.3 启动开发服务器

```bash
# 方式1: 直接启动
python src/main.py --reload

# 方式2: 使用uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 方式3: Docker
make dev
```

### 1.4 VSCode 配置

创建 `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

---

## 2. 项目结构

### 2.1 目录组织

```
miaota_industrial_agent/
├── src/                        # 源代码
│   ├── api/                    # API层 (接口定义)
│   │   ├── __init__.py
│   │   ├── gateway.py          # 网关
│   │   ├── auth.py             # 认证API
│   │   ├── data_api.py         # 数据API
│   │   ├── alert_api.py        # 告警API
│   │   ├── rule_api.py         # 规则API
│   │   ├── diagnosis_api.py    # 诊断API
│   │   ├── report_api.py       # 报表API
│   │   └── websocket_server.py # WebSocket
│   │
│   ├── core/                   # 核心模块 (业务逻辑)
│   │   ├── __init__.py
│   │   ├── tag_mapping.py      # 点位映射
│   │   ├── config_manager.py   # 配置管理
│   │   ├── event_bus.py        # 事件总线
│   │   └── audit_logger.py     # 审计日志
│   │
│   ├── data/                   # 数据层
│   │   ├── __init__.py
│   │   ├── collector.py        # PLC采集
│   │   ├── buffer.py           # 数据缓存
│   │   ├── compression.py      # 数据压缩
│   │   ├── storage.py          # 存储抽象
│   │   ├── influx_storage.py   # InfluxDB
│   │   ├── sqlite_storage.py   # SQLite
│   │   └── preprocessor.py     # 数据预处理
│   │
│   ├── rules/                  # 规则引擎
│   │   ├── __init__.py
│   │   ├── rule_engine.py      # 规则执行
│   │   ├── rule_types.py       # 规则类型
│   │   └── escalation.py       # 告警升级
│   │
│   ├── models/                 # AI/ML模型
│   │   ├── __init__.py
│   │   ├── anomaly_detection.py
│   │   ├── multi_variate_detection.py
│   │   ├── adaptive_threshold.py
│   │   ├── forecasting/        # 时序预测
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── prophet_model.py
│   │   │   ├── arima_model.py
│   │   │   ├── lstm_model.py
│   │   │   └── model_manager.py
│   │   ├── llm_diagnosis.py
│   │   ├── diagnosis_report.py
│   │   └── feature_engineering.py
│   │
│   ├── knowledge/              # 知识库(RAG)
│   │   ├── __init__.py
│   │   ├── document_loader.py
│   │   ├── document_chunker.py
│   │   ├── vector_store.py
│   │   └── rag_engine.py
│   │
│   ├── utils/                  # 工具类
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── report_exporter.py
│   │   └── data_quality.py
│   │
│   └── web/                    # Web前端
│       ├── static/
│       ├── templates/
│       └── app.py
│
├── security/                   # 安全模块
│   ├── __init__.py
│   ├── auth.py
│   ├── rbac.py
│   ├── audit.py
│   └── compliance.py
│
├── tests/                      # 测试代码
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   ├── e2e/                    # 端到端测试
│   └── conftest.py             # pytest配置
│
├── config/                     # 配置
│   ├── settings.yaml
│   └── rules/
│
├── docs/                       # 文档
│   ├── user_manual.md
│   ├── api_reference.md
│   ├── deployment.md
│   └── development.md
│
├── scripts/                    # 脚本
│   ├── start.sh
│   ├── stop.sh
│   ├── backup.sh
│   └── setup.sh
│
├── docker/                     # Docker配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
│
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── Makefile                    # 构建脚本
├── CHANGELOG.md                # 版本历史
├── PROJECT_STATUS.md           # 项目状态
├── REQUIREMENTS_SPEC.md        # 需求规格
└── README.md                   # 项目说明
```

### 2.2 模块职责

| 模块 | 职责 | 关键类 |
|------|------|--------|
| api | 接口层 | FastAPI路由 |
| core | 业务核心 | 领域模型、业务逻辑 |
| data | 数据访问 | 存储抽象、数据转换 |
| rules | 规则引擎 | 规则定义、执行引擎 |
| models | AI模型 | 检测、预测、诊断 |
| knowledge | 知识库 | RAG引擎、文档处理 |
| utils | 工具 | 日志、导出、质量 |
| security | 安全 | 认证、权限、审计 |

---

## 3. 代码规范

### 3.1 Python 代码规范

遵循 [PEP 8](https://pep8.org/) 和 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块名 | 小写，下划线分隔 | `data_collector.py` |
| 类名 | 大驼峰 | `DataCollector` |
| 函数名 | 小写，下划线分隔 | `collect_data()` |
| 常量 | 大写，下划线分隔 | `MAX_RETRY_COUNT` |
| 私有变量 | 下划线前缀 | `_internal_data` |

#### 代码格式

使用 Black 进行代码格式化:

```bash
# 格式化单个文件
black src/data/collector.py

# 格式化整个项目
black src/

# 检查格式
black --check src/
```

#### 导入排序

使用 isort 进行导入排序:

```bash
isort src/
```

#### 类型注解

强制使用类型注解:

```python
from typing import List, Dict, Optional

def process_data(
    data: List[Dict[str, float]],
    threshold: float = 0.5
) -> Optional[Dict[str, any]]:
    """处理数据并返回结果.
    
    Args:
        data: 输入数据列表
        threshold: 阈值
        
    Returns:
        处理结果，失败返回None
    """
    pass
```

### 3.2 文档字符串规范

使用 Google Style 文档字符串:

```python
def calculate_anomaly_score(
    values: np.ndarray,
    algorithm: str = "isolation_forest"
) -> np.ndarray:
    """计算异常分数.
    
    使用机器学习算法计算输入数据的异常分数。
    
    Args:
        values: 输入数据数组，形状为 (n_samples, n_features)
        algorithm: 异常检测算法，可选值为:
            - "isolation_forest": 孤立森林
            - "lof": 局部异常因子
            - "mahalanobis": 马氏距离
            
    Returns:
        异常分数数组，形状为 (n_samples,)，
        分数越大表示越异常
        
    Raises:
        ValueError: 当algorithm参数不合法时
        RuntimeError: 当模型训练失败时
        
    Example:
        >>> data = np.random.randn(100, 5)
        >>> scores = calculate_anomaly_score(data, "isolation_forest")
        >>> print(f"异常样本数: {(scores > 0.5).sum()}")
    """
    pass
```

### 3.3 错误处理

```python
from loguru import logger

class DataCollectionError(Exception):
    """数据采集异常."""
    pass

def collect_plc_data(plc_config: Dict) -> List[Dict]:
    """采集PLC数据."""
    try:
        # 连接PLC
        plc = connect_plc(plc_config)
        
        # 读取数据
        data = plc.read_data()
        
        return data
        
    except ConnectionError as e:
        logger.error(f"PLC连接失败: {e}")
        raise DataCollectionError(f"无法连接到PLC: {plc_config['host']}") from e
        
    except TimeoutError as e:
        logger.warning(f"PLC读取超时: {e}")
        # 返回缓存数据
        return get_cached_data(plc_config['name'])
        
    except Exception as e:
        logger.exception(f"未知错误: {e}")
        raise
```

### 3.4 日志规范

```python
from loguru import logger

# 正确用法
logger.info("开始数据采集")
logger.debug("原始数据: {}", raw_data)
logger.warning("数据质量警告: 缺失值 {}%", missing_rate * 100)
logger.error("PLC连接失败: {}", error_msg)
logger.exception("处理异常")  # 自动包含堆栈

# 结构化日志
logger.info(
    "数据上报完成",
    extra={
        "tag_count": len(tags),
        "data_points": total_points,
        "duration_ms": elapsed_time
    }
)
```

---

## 4. 测试指南

### 4.1 测试结构

```
tests/
├── conftest.py           # pytest配置和fixture
├── unit/                 # 单元测试
│   ├── test_data/
│   ├── test_rules/
│   ├── test_models/
│   └── test_core/
├── integration/          # 集成测试
│   ├── test_api/
│   ├── test_storage/
│   └── test_collector/
└── e2e/                  # 端到端测试
    └── test_workflows/
```

### 4.2 单元测试

```python
# tests/unit/test_rules/test_rule_engine.py
import pytest
from src.rules.rule_engine import RuleEngine
from src.rules.rule_types import ThresholdRule

class TestRuleEngine:
    """规则引擎单元测试."""
    
    @pytest.fixture
    def engine(self):
        return RuleEngine()
    
    def test_threshold_rule_trigger(self, engine):
        """测试阈值规则触发."""
        # Arrange
        rule = ThresholdRule(
            name="test_rule",
            tag="temperature",
            operator=">",
            threshold=100.0
        )
        engine.add_rule(rule)
        
        # Act
        result = engine.evaluate({"temperature": 105.0})
        
        # Assert
        assert result.triggered is True
        assert result.rule_name == "test_rule"
    
    def test_threshold_rule_not_trigger(self, engine):
        """测试阈值规则不触发."""
        rule = ThresholdRule(
            name="test_rule",
            tag="temperature",
            operator=">",
            threshold=100.0
        )
        engine.add_rule(rule)
        
        result = engine.evaluate({"temperature": 95.0})
        
        assert result.triggered is False
    
    @pytest.mark.parametrize("value,expected", [
        (105.0, True),
        (100.0, False),
        (95.0, False),
    ])
    def test_threshold_boundary(self, engine, value, expected):
        """测试阈值边界条件."""
        rule = ThresholdRule(
            name="test_rule",
            tag="temperature",
            operator=">",
            threshold=100.0
        )
        engine.add_rule(rule)
        
        result = engine.evaluate({"temperature": value})
        assert result.triggered is expected
```

### 4.3 集成测试

```python
# tests/integration/test_api/test_data_api.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

class TestDataAPI:
    """数据API集成测试."""
    
    def test_get_realtime_data(self):
        """测试获取实时数据."""
        response = client.get("/api/v1/data/realtime?tags=DO_CONCENTRATION")
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "data" in data
    
    def test_query_history_data(self):
        """测试查询历史数据."""
        response = client.get(
            "/api/v1/data/history",
            params={
                "tag": "DO_CONCENTRATION",
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tag"] == "DO_CONCENTRATION"
        assert "data" in data
```

### 4.4 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_rules/

# 运行并生成覆盖率报告
pytest --cov=src --cov-report=html

# 运行并显示详细输出
pytest -v

# 运行失败的测试
pytest --lf

# 并行运行测试
pytest -n auto
```

### 4.5 测试覆盖率要求

| 模块 | 覆盖率要求 |
|------|-----------|
| core | ≥ 90% |
| data | ≥ 85% |
| rules | ≥ 90% |
| models | ≥ 80% |
| api | ≥ 85% |

---

## 5. 贡献指南

### 5.1 贡献流程

1. **Fork 仓库**
2. **创建分支**: `git checkout -b feature/your-feature`
3. **提交更改**: `git commit -m "feat: add new feature"`
4. **推送分支**: `git push origin feature/your-feature`
5. **创建 Pull Request**

### 5.2 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:

- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具

**示例**:

```
feat(rules): 添加告警升级功能

- 实现4级升级策略
- 支持多渠道通知
- 添加自动工单创建

Closes #123
```

### 5.3 PR检查清单

- [ ] 代码遵循项目规范
- [ ] 添加/更新了测试
- [ ] 测试通过
- [ ] 更新了文档
- [ ] 更新了CHANGELOG

### 5.4 代码审查

审查关注点:

1. **正确性**: 代码逻辑是否正确
2. **可读性**: 代码是否易于理解
3. **性能**: 是否有性能问题
4. **安全性**: 是否存在安全隐患
5. **测试**: 测试是否充分
6. **文档**: 是否有必要注释

---

## 6. 架构设计

### 6.1 架构原则

1. **单一职责**: 每个模块只负责一个功能
2. **依赖倒置**: 依赖抽象而非具体实现
3. **开闭原则**: 对扩展开放，对修改封闭
4. **接口隔离**: 提供精简的接口

### 6.2 核心设计模式

#### 发布-订阅模式 (事件总线)

```python
# src/core/event_bus.py
from typing import Callable, Dict, List

class EventBus:
    """事件总线."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def publish(self, event_type: str, data: any):
        """发布事件."""
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            handler(data)

# 使用
bus = EventBus()

# 订阅
bus.subscribe("data.received", lambda data: print(data))

# 发布
bus.publish("data.received", {"value": 3.5})
```

#### 策略模式 (异常检测)

```python
from abc import ABC, abstractmethod

class AnomalyDetectionStrategy(ABC):
    """异常检测策略."""
    
    @abstractmethod
    def detect(self, data: np.ndarray) -> np.ndarray:
        pass

class IsolationForestStrategy(AnomalyDetectionStrategy):
    def detect(self, data: np.ndarray) -> np.ndarray:
        model = IsolationForest()
        return model.fit_predict(data)

class LOFStrategy(AnomalyDetectionStrategy):
    def detect(self, data: np.ndarray) -> np.ndarray:
        model = LocalOutlierFactor()
        return model.fit_predict(data)

class AnomalyDetector:
    def __init__(self, strategy: AnomalyDetectionStrategy):
        self._strategy = strategy
    
    def detect(self, data: np.ndarray) -> np.ndarray:
        return self._strategy.detect(data)

# 使用
detector = AnomalyDetector(IsolationForestStrategy())
```

#### 工厂模式 (模型创建)

```python
class ForecastModelFactory:
    """预测模型工厂."""
    
    _models = {
        "prophet": ProphetModel,
        "arima": ARIMAModel,
        "lstm": LSTMModel,
    }
    
    @classmethod
    def create(cls, model_type: str) -> ForecastModel:
        if model_type not in cls._models:
            raise ValueError(f"Unknown model type: {model_type}")
        return cls._models[model_type]()
```

### 6.3 数据流

```
PLC设备
   │
   ▼
采集器 (Collector)
   │
   ├─▶ 数据缓存 (Buffer) ──▶ 补传
   │
   ▼
数据预处理 (Preprocessor)
   │
   ├─▶ 规则引擎 (RuleEngine) ──▶ 告警
   │
   ├─▶ 异常检测 (AnomalyDetector)
   │
   ▼
存储层 (Storage)
   ├─▶ InfluxDB (时序数据)
   ├─▶ SQLite (关系数据)
   └─▶ ChromaDB (向量数据)
```

### 6.4 扩展点

如需扩展功能，请使用以下扩展点:

| 扩展点 | 接口 | 示例 |
|--------|------|------|
| 新PLC协议 | `BaseCollector` | 实现OPC UA采集器 |
| 新存储后端 | `BaseStorage` | 实现MongoDB存储 |
| 新检测算法 | `AnomalyDetectionStrategy` | 实现LSTM检测 |
| 新预测模型 | `ForecastModel` | 实现XGBoost预测 |
| 新通知渠道 | `NotificationChannel` | 实现企业微信通知 |

---

## 附录

### A. 常用命令

```bash
# 格式化代码
make format

# 运行测试
make test

# 构建Docker镜像
make build

# 部署到开发环境
make deploy-dev

# 部署到生产环境
make deploy-prod
```

### B. 推荐阅读

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [scikit-learn 文档](https://scikit-learn.org/)

---

**文档版本**: v1.0.0-beta1  
**最后更新**: 2026-03-26
