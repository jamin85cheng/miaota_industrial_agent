# Miaota Industrial Agent - 工业智能监控与预测系统

🦞 基于 LLM 的工业三废 (废气/废水/粉尘) 智能监控、异常检测、故障预测与自进化系统。

## 🎯 项目目标

从 PLC 原始数据出发，构建具备**自进化能力**的工业智能体：
1. **数字化与感知** - 将 PLC"哑数据"变成"有标签的知识"
2. **专用智能体** - 在特定场景下达到专家水平
3. **闭环自动化** - 小问题自动处理，大问题辅助决策
4. **自进化生态** - 模型越用越聪明，无需大量人工干预

## 🏗️ 架构设计

```
miaota_industrial_agent/
├── src/
│   ├── core/              # 核心引擎
│   │   ├── __init__.py
│   │   ├── data_pipeline.py    # 数据采集与清洗
│   │   ├── tag_mapping.py      # 点位语义化映射
│   │   └── label_engine.py     # 标签工厂
│   ├── data/              # 数据处理
│   │   ├── __init__.py
│   │   ├── collector.py        # PLC 数据采集
│   │   ├── storage.py          # 时序数据存储
│   │   └── preprocessor.py     # 数据预处理
│   ├── models/            # AI 模型
│   │   ├── __init__.py
│   │   ├── anomaly_detection.py # 异常检测 (Isolation Forest/LSTM)
│   │   ├── forecasting.py       # 趋势预测 (NeuralProphet)
│   │   └── llm_diagnosis.py     # LLM 诊断引擎
│   ├── rules/             # 规则引擎
│   │   ├── __init__.py
│   │   ├── rule_parser.py      # 规则 DSL 解析
│   │   ├── rule_engine.py      # 规则执行引擎
│   │   └── default_rules.json  # 默认规则库
│   ├── knowledge/         # 知识库
│   │   ├── __init__.py
│   │   ├── rag_engine.py         # RAG 检索增强生成
│   │   ├── vector_store.py       # 向量数据库
│   │   └── document_loader.py    # 文档加载与分块
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── logger.py             # 日志配置
│       ├── config.py             # 配置管理
│       └── metrics.py            # 评估指标
├── config/                # 配置文件
│   ├── settings.yaml      # 系统配置
│   ├── tag_mapping.xlsx   # 点位映射表
│   └── rules.json         # 规则定义
├── data/                  # 数据目录
│   ├── raw/               # 原始数据
│   ├── processed/         # 处理后数据
│   └── knowledge_base/    # 知识库文档
├── tests/                 # 测试用例
├── notebooks/             # Jupyter 实验笔记
├── scripts/               # 运维脚本
│   ├── start.sh           # 启动脚本
│   ├── train.sh           # 训练脚本
│   └── deploy.sh          # 部署脚本
├── docs/                  # 文档
├── requirements.txt       # Python 依赖
├── docker-compose.yml     # Docker 编排
├── Dockerfile             # 容器镜像
└── README.md              # 本文件
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/jamin85cheng/miaota_industrial_agent.git
cd miaota_industrial_agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config/settings.yaml`，配置数据库连接、PLC 参数等。

### 3. 准备点位映射表

填写 `config/tag_mapping.xlsx`，定义 PLC 地址与业务含义的映射关系。

### 4. 启动数据采集

```bash
python src/data/collector.py --config config/settings.yaml
```

### 5. 运行规则引擎

```bash
python src/rules/rule_engine.py --config config/rules.json
```

### 6. 启动 RAG 知识库

```bash
python src/knowledge/rag_engine.py --init
```

### 7. 查看监控大屏

访问 `http://localhost:8501` (Streamlit 界面)

## 📦 核心功能模块

### 模块 A: 点位映射管理 (Tag Mapping)

将 PLC 寄存器地址转换为业务语义：

```python
from src.core.tag_mapping import TagMapper

mapper = TagMapper('config/tag_mapping.xlsx')
semantic_data = mapper.translate(raw_plc_data)
# 输出：{"曝气池溶解氧_DO": 3.5, "1#提升泵_状态": True}
```

### 模块 B: 规则引擎 (Rule Engine)

基于专家经验自动标注工况：

```python
from src.rules.rule_engine import RuleEngine

engine = RuleEngine('config/rules.json')
labels = engine.evaluate(time_series_data)
# 输出：[{"timestamp": "...", "label": "缺氧异常", "severity": "high"}]
```

### 模块 C: 无监督聚类 (Anomaly Detection)

自动发现未知异常模式：

```python
from src.models.anomaly_detection import AnomalyDetector

detector = AnomalyDetector(method='isolation_forest')
anomalies = detector.detect(data)
# 输出：异常点位置、得分、聚类结果
```

### 模块 D: 知识库 RAG (Knowledge Base)

LLM 驱动的智能诊断：

```python
from src.knowledge.rag_engine import RAGEngine

rag = RAGEngine(knowledge_dir='data/knowledge_base')
response = rag.query("DO 突然下降怎么办？")
# 输出：诊断报告 + 相似案例 + 处置建议
```

## 🔧 技术栈

- **语言**: Python 3.9+
- **PLC 通信**: python-snap7 (西门子), pymodbus (Modbus)
- **时序数据库**: InfluxDB / IoTDB
- **向量数据库**: Chroma / FAISS
- **机器学习**: scikit-learn, PyTorch
- **LLM**: Qwen2.5 / ChatGLM3 (通过 Ollama 或 Transformers)
- **RAG 框架**: LangChain
- **可视化**: Streamlit / ECharts
- **部署**: Docker, Docker Compose

## 📊 数据流程图

```
PLC → 数据采集 → 语义化映射 → 规则标注 → 时序数据库
                                    ↓
                              异常检测模型
                                    ↓
                              LLM 诊断引擎 ← 知识库 (RAG)
                                    ↓
                              监控大屏 + 告警推送
                                    ↓
                              人工反馈收集
                                    ↓
                              模型增量微调 (自进化)
```

## 🎯 阶段规划

### ✅ 阶段一：数字化与感知 (当前)
- [x] 项目骨架搭建
- [ ] 点位映射工具完成
- [ ] 规则引擎上线
- [ ] 初始知识库构建

### ⏳ 阶段二：专用智能体
- [ ] LLM 微调 pipeline
- [ ] 人机反馈收集系统
- [ ] 诊断准确率>85%

### ⏳ 阶段三：闭环自动化
- [ ] 安全控制指令下发
- [ ] 数字孪生仿真沙箱
- [ ] 自动效果评估

### ⏳ 阶段四：自进化生态
- [ ] 在线学习 pipeline
- [ ] 多智能体协作
- [ ] 跨工厂迁移学习

## 📝 许可证

MIT License

## 👥 团队

Created by Jamin OpenClaw 🦞

---

**下一步**: 填写配置文件，接入你的 PLC 数据，开始智能化之旅！
