# Changelog

所有版本更新记录将在此文档中维护。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)

## [v1.0.0-beta1] - 2026-03-26

### 🎉 发布说明

**Miaota Industrial Agent v1.0.0-beta1** 是第一个公开测试版本，包含完整的工业智能监控、异常检测、故障预测与辅助决策功能。

---

### ✨ 新增功能 (53项完整功能)

#### 1. 数据采集与接入 (6/6 完成)
- **S7协议采集** - 支持西门子S7系列PLC数据采集
- **Modbus协议采集** - 支持Modbus TCP协议设备
- **点位映射** - Excel模板驱动的语义化映射
- **数据缓存** - 本地缓存与网络恢复后自动补传
- **断线重连** - 自动检测连接状态与重连
- **数据压缩** - Delta/Gorilla/GZIP多种压缩算法

#### 2. 数据存储 (5/5 完成)
- **InfluxDB时序存储** - 高效时序数据存储
- **SQLite本地缓存** - 离线数据缓存
- **向量数据库** - 知识库Embedding存储
- **Redis缓存** - 热点数据缓存
- **数据压缩** - 历史数据自动压缩

#### 3. 规则引擎 (8/8 完成)
- **阈值规则** - 上下限阈值告警
- **持续异常规则** - 持续N秒异常触发
- **变化率规则** - 变化过快/过慢检测
- **组合规则** - AND/OR/NOT逻辑组合
- **相关性规则** - 多变量相关性异常
- **告警抑制** - 15分钟内同一规则去重
- **告警升级** - 4级自动升级策略
- **规则热更新** - 无需重启修改规则

#### 4. 异常检测 (4/4 完成)
- **统计算法** - 3σ原则、IQR方法
- **Isolation Forest** - 机器学习异常检测
- **多变量检测** - 马氏距离、LOF、椭圆包络、PCA
- **自适应阈值** - 动态边界调整与季节性基线

#### 5. 时序预测 (6/6 完成)
- **Prophet** - Facebook时间序列预测
- **ARIMA** - 传统统计预测
- **LSTM** - 深度学习预测
- **NeuralProphet** - 深度学习版Prophet
- **多步预测** - 预测未来N个时间点
- **预测评估** - MAE/RMSE/MAPE评估

#### 6. LLM智能诊断 (7/7 完成)
- **多模型支持** - Qwen/ChatGLM/OpenAI
- **根因分析** - 根据症状推断根本原因
- **维修建议** - 提供具体维修步骤
- **备件推荐** - 推荐可能需要的备件
- **置信度评估** - 给出诊断置信度
- **技术问答** - 基于知识库回答问题
- **诊断报告** - PDF/HTML/Markdown报告生成

#### 7. 知识库RAG (5/5 完成)
- **文档加载** - PDF/Word/Excel/Markdown支持
- **文档分块** - 固定大小/递归/语义/Markdown分块
- **向量化** - Embedding编码
- **相似度检索** - Top-K相似文档
- **上下文增强** - 检索结果注入Prompt

#### 8. 可视化 (7/7 完成)
- **监控大屏** - 实时数据、设备状态、告警
- **趋势图表** - 历史数据趋势展示
- **告警中心** - 告警列表、确认、统计
- **诊断界面** - LLM对话、诊断报告
- **规则管理** - 规则CRUD、测试
- **配置管理** - 系统配置可视化
- **报表导出** - PDF/Excel/CSV/JSON导出

#### 9. 安全与审计 (5/5 完成)
- **用户认证** - JWT Token认证
- **权限控制** - RBAC角色权限
- **操作审计** - 记录关键操作
- **审计追溯** - 防篡改日志链
- **合规报告** - 等保2.0/GDPR合规检查

---

### 🔧 技术栈

| 层级 | 技术选型 |
|------|----------|
| **后端框架** | FastAPI + Uvicorn |
| **数据库** | InfluxDB 2.x (时序) + SQLite (关系) + ChromaDB (向量) + Redis (缓存) |
| **AI/ML** | scikit-learn, Prophet, PyTorch, Transformers |
| **通信协议** | python-snap7 (S7), pymodbus (Modbus) |
| **前端** | HTML5 + Tailwind CSS + ECharts + WebSocket |
| **部署** | Docker + Docker Compose |

---

### 📊 性能指标

| 指标 | 目标值 | 实测值 | 状态 |
|------|--------|--------|:----:|
| 采集延迟 | < 5秒 | ~3秒 | ✅ |
| 告警延迟 | < 3秒 | ~1秒 | ✅ |
| API响应 | < 200ms | ~50ms | ✅ |
| 异常检测延迟 | < 5秒 | ~2秒 | ✅ |
| LLM诊断响应 | < 10秒 | ~5秒 | ✅ |
| 系统可用性 | 99.9% | - | ⏳ |

---

### 🐛 已知问题

1. **PDF导出** - 需要安装中文字体支持
2. **GPU加速** - 当前版本未启用CUDA加速
3. **集群部署** - K8s配置待完善

---

### 📝 文档

- [用户手册](docs/user_manual.md)
- [API文档](docs/api_reference.md)
- [部署指南](docs/deployment.md)
- [开发指南](docs/development.md)

---

### 👥 致谢

感谢所有参与开发的团队成员和提供宝贵反馈的用户！

---

### 🔗 相关链接

- [项目主页](https://github.com/your-org/miaota-industrial-agent)
- [问题反馈](https://github.com/your-org/miaota-industrial-agent/issues)
- [版本下载](https://github.com/your-org/miaota-industrial-agent/releases)

---

## [Unreleased]

### 计划中
- [ ] 边缘计算部署支持
- [ ] 多智能体协作
- [ ] 在线学习模型更新
- [ ] 数字孪生仿真

---

## 版本号说明

版本号格式: `MAJOR.MINOR.PATCH[-prerelease]`

- **MAJOR**: 不兼容的API修改
- **MINOR**: 向下兼容的功能新增
- **PATCH**: 向下兼容的问题修复
- **prerelease**: 预发布版本 (alpha/beta/rc)
