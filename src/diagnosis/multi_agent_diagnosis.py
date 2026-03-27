"""
多智能体协同诊断系统

基于 MiroFish 群体智能理念的多专家诊断引擎
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from src.utils.structured_logging import get_logger
from src.utils.thread_safe import ThreadSafeDict

logger = get_logger("multi_agent_diagnosis")


class ExpertType(Enum):
    """专家类型"""
    MECHANICAL = "mechanical"      # 机械专家
    ELECTRICAL = "electrical"      # 电气专家
    PROCESS = "process"            # 工艺专家
    SENSOR = "sensor"              # 传感器专家
    HISTORICAL = "historical"      # 历史案例专家
    COORDINATOR = "coordinator"    # 协调者


@dataclass
class ExpertOpinion:
    """专家意见"""
    expert_type: ExpertType
    expert_name: str
    confidence: float              # 0-1
    root_cause: str
    evidence: List[str]
    suggestions: List[str]
    reasoning: str                 # 推理过程
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expert_type": self.expert_type.value,
            "expert_name": self.expert_name,
            "confidence": self.confidence,
            "root_cause": self.root_cause,
            "evidence": self.evidence,
            "suggestions": self.suggestions,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MultiAgentDiagnosisResult:
    """多智能体诊断结果"""
    diagnosis_id: str
    symptoms: str
    final_conclusion: str
    confidence: float
    consensus_level: float         # 专家一致性程度
    expert_opinions: List[ExpertOpinion]
    dissenting_views: List[ExpertOpinion]  # 不同意见
    recommended_actions: List[Dict[str, Any]]
    spare_parts: List[Dict[str, Any]]
    related_cases: List[str]
    simulation_scenarios: List[Dict[str, Any]]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "symptoms": self.symptoms,
            "final_conclusion": self.final_conclusion,
            "confidence": self.confidence,
            "consensus_level": self.consensus_level,
            "expert_opinions": [op.to_dict() for op in self.expert_opinions],
            "dissenting_views": [op.to_dict() for op in self.dissenting_views],
            "recommended_actions": self.recommended_actions,
            "spare_parts": self.spare_parts,
            "related_cases": self.related_cases,
            "simulation_scenarios": self.simulation_scenarios,
            "generated_at": self.generated_at.isoformat()
        }


class LLMExpertAgent:
    """LLM驱动的专家智能体"""
    
    def __init__(self, expert_type: ExpertType, name: str, system_prompt: str, llm_client=None):
        self.expert_type = expert_type
        self.name = name
        self.system_prompt = system_prompt
        self.llm_client = llm_client
        self.memory = []  # 对话历史
        
    async def analyze(self, symptoms: str, sensor_data: Dict[str, Any], 
                     context: Dict[str, Any] = None) -> ExpertOpinion:
        """
        分析问题并给出专业意见
        
        Args:
            symptoms: 症状描述
            sensor_data: 传感器数据
            context: 额外上下文
        
        Returns:
            ExpertOpinion: 专家意见
        """
        # 构建提示词
        prompt = self._build_prompt(symptoms, sensor_data, context)
        
        # 调用LLM
        try:
            response = await self._call_llm(prompt)
            opinion = self._parse_response(response)
            opinion.expert_type = self.expert_type
            opinion.expert_name = self.name
            return opinion
        except Exception as e:
            logger.error(f"专家 {self.name} 分析失败: {e}")
            return self._create_fallback_opinion(symptoms)
    
    def _build_prompt(self, symptoms: str, sensor_data: Dict[str, Any], 
                     context: Dict[str, Any] = None) -> str:
        """构建提示词"""
        prompt = f"""{self.system_prompt}

## 当前故障症状
{symptoms}

## 传感器数据
{json.dumps(sensor_data, indent=2, ensure_ascii=False)}

"""
        if context:
            prompt += f"""## 额外上下文
{json.dumps(context, indent=2, ensure_ascii=False)}

"""
        
        prompt += """## 输出要求
请按以下JSON格式输出诊断意见：
{
    "confidence": 0.85,
    "root_cause": "根因描述",
    "evidence": ["证据1", "证据2"],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "详细的推理过程"
}
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM（简化版，实际应调用真实LLM API）"""
        # 这里使用模拟响应，实际应调用OpenAI/Claude等API
        return self._generate_mock_response(prompt)
    
    def _generate_mock_response(self, prompt: str) -> str:
        """生成模拟响应（用于演示）"""
        # 根据专家类型返回不同的模拟响应
        mock_responses = {
            ExpertType.MECHANICAL: {
                "confidence": 0.82,
                "root_cause": "曝气盘部分堵塞，导致曝气效率下降40%",
                "evidence": [
                    "振动频谱分析显示异常峰值在轴承特征频率处",
                    "温度梯度变化符合机械磨损模式"
                ],
                "suggestions": [
                    "检查并清洗曝气盘",
                    "检查风机叶轮是否平衡",
                    "更换老化机械密封"
                ],
                "reasoning": "通过振动频谱分析，发现..."
            },
            ExpertType.ELECTRICAL: {
                "confidence": 0.75,
                "root_cause": "电机绝缘老化，电流不平衡度超过15%",
                "evidence": [
                    "三相电流不平衡度：A相12.5A, B相11.8A, C相13.2A",
                    "绝缘电阻测试值低于标准阈值"
                ],
                "suggestions": [
                    "进行电机绝缘处理或更换",
                    "检查供电电压稳定性",
                    "调整变频器参数"
                ],
                "reasoning": "电流不平衡度计算显示..."
            },
            ExpertType.PROCESS: {
                "confidence": 0.88,
                "root_cause": "污泥龄过长导致污泥活性下降",
                "evidence": [
                    "污泥浓度(MLSS)持续高于4000mg/L",
                    "污泥体积指数(SVI)超过200mL/g"
                ],
                "suggestions": [
                    "加大排泥量，控制污泥龄在15-20天",
                    "调整进水负荷分配",
                    "考虑添加营养剂"
                ],
                "reasoning": "根据活性污泥法原理..."
            },
            ExpertType.SENSOR: {
                "confidence": 0.90,
                "root_cause": "DO传感器探头污染导致读数漂移",
                "evidence": [
                    "DO读数与理论计算值偏差超过20%",
                    "传感器校准记录已超期30天"
                ],
                "suggestions": [
                    "清洗并校准DO传感器",
                    "建立定期维护计划",
                    "考虑增加冗余传感器"
                ],
                "reasoning": "传感器数据分析显示..."
            },
            ExpertType.HISTORICAL: {
                "confidence": 0.70,
                "root_cause": "与2023-08-15案例相似，疑似进水负荷冲击",
                "evidence": [
                    "历史相似度匹配得分0.85",
                    "相同时间段出现相似症状"
                ],
                "suggestions": [
                    "参考历史案例处理方法",
                    "加强进水水质监测",
                    "准备应急处理方案"
                ],
                "reasoning": "基于知识图谱相似度匹配..."
            }
        }
        
        response = mock_responses.get(self.expert_type, mock_responses[ExpertType.MECHANICAL])
        return json.dumps(response, ensure_ascii=False)
    
    def _parse_response(self, response: str) -> ExpertOpinion:
        """解析LLM响应"""
        try:
            data = json.loads(response)
            return ExpertOpinion(
                expert_type=self.expert_type,
                expert_name=self.name,
                confidence=data.get("confidence", 0.5),
                root_cause=data.get("root_cause", "未知"),
                evidence=data.get("evidence", []),
                suggestions=data.get("suggestions", []),
                reasoning=data.get("reasoning", "")
            )
        except json.JSONDecodeError:
            return self._create_fallback_opinion(response)
    
    def _create_fallback_opinion(self, symptoms: str) -> ExpertOpinion:
        """创建默认意见（失败时使用）"""
        return ExpertOpinion(
            expert_type=self.expert_type,
            expert_name=self.name,
            confidence=0.3,
            root_cause="无法确定根因",
            evidence=["数据不足"],
            suggestions=["请提供更多数据", "联系技术支持"],
            reasoning="分析过程中出现错误"
        )


class MultiAgentDiagnosisEngine:
    """
    多智能体协同诊断引擎
    
    模拟多个领域专家协作诊断的过程
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.experts: Dict[ExpertType, LLMExpertAgent] = {}
        self.coordinator: Optional[LLMExpertAgent] = None
        self._init_experts()
        
        # 诊断历史
        self._diagnosis_history = ThreadSafeDict()
    
    def _init_experts(self):
        """初始化专家团队"""
        experts_config = [
            {
                "type": ExpertType.MECHANICAL,
                "name": "机械故障诊断专家",
                "prompt": """你是资深的机械设备故障诊断专家，拥有20年旋转机械维护经验。

你的专长包括：
- 振动分析与频谱诊断
- 轴承故障模式识别
- 机械密封失效分析
- 动平衡与对中问题

分析时请重点关注：
1. 振动频谱特征
2. 温度分布异常
3. 磨损模式识别
4. 机械间隙变化

给出意见时请明确：
- 故障概率评估
- 发展速度与风险评估
- 维修紧急程度
"""
            },
            {
                "type": ExpertType.ELECTRICAL,
                "name": "电气系统诊断专家",
                "prompt": """你是电气系统诊断专家，精通电机驱动与控制系统。

你的专长包括：
- 三相电流不平衡分析
- 电机绝缘状态评估
- 变频器故障诊断
- 电气保护系统分析

分析时请重点关注：
1. 电流电压波形异常
2. 绝缘电阻趋势
3. 谐波畸变率
4. 保护装置动作记录

给出意见时请明确：
- 电气安全风险等级
- 对生产的影响程度
- 建议停电检查项目
"""
            },
            {
                "type": ExpertType.PROCESS,
                "name": "工艺分析专家",
                "prompt": """你是污水处理工艺专家，精通活性污泥法工艺控制。

你的专长包括：
- 污泥龄(SRT)优化
- 溶解氧(DO)控制策略
- 营养物平衡分析
- 污泥沉降性能评估

分析时请重点关注：
1. 污泥浓度(MLSS/MLVSS)
2. 沉降比(SV30)和SVI
3. 食微比(F/M)
4. 营养比(BOD:N:P)

给出意见时请明确：
- 工艺调整方向
- 参数优化建议
- 出水达标风险评估
"""
            },
            {
                "type": ExpertType.SENSOR,
                "name": "传感器与仪表专家",
                "prompt": """你是工业自动化仪表专家，精通各类传感器故障诊断。

你的专长包括：
- 在线分析仪表校准
- 传感器漂移诊断
- 信号干扰分析
- 测量系统不确定度评估

分析时请重点关注：
1. 测量值合理性检查
2. 传感器校准状态
3. 信号噪声分析
4. 仪表响应时间

给出意见时请明确：
- 传感器是否需要校准/更换
- 测量数据可信度
- 建议的仪表维护措施
"""
            },
            {
                "type": ExpertType.HISTORICAL,
                "name": "历史案例匹配专家",
                "prompt": """你是知识管理专家，擅长从历史案例中识别相似模式。

你的专长包括：
- 故障案例库检索
- 相似度计算与匹配
- 历史处理效果评估
- 知识图谱推理

分析时请重点关注：
1. 症状相似度匹配
2. 处理方案有效性
3. 历史处理时间线
4. 复发风险评估

给出意见时请明确：
- 最相似的历史案例
- 参考的处理方案
- 预期恢复时间
"""
            }
        ]
        
        for config in experts_config:
            expert = LLMExpertAgent(
                expert_type=config["type"],
                name=config["name"],
                system_prompt=config["prompt"],
                llm_client=self.llm_client
            )
            self.experts[config["type"]] = expert
        
        # 初始化协调者
        self.coordinator = LLMExpertAgent(
            expert_type=ExpertType.COORDINATOR,
            name="诊断协调专家",
            system_prompt="""你是诊断协调专家，负责整合多位专家的意见形成最终诊断结论。

你的职责：
1. 分析各专家意见的共识与分歧
2. 识别高置信度的结论
3. 整合形成一致的处理建议
4. 明确标注不确定性和风险

输出要求：
- 最终根因结论（综合各专家意见）
- 置信度评估
- 共识程度说明
- 分步处理建议（按优先级排序）
- 需要的备件清单
- 风险评估
""",
            llm_client=self.llm_client
        )
    
    async def diagnose(self, symptoms: str, sensor_data: Dict[str, Any],
                      context: Dict[str, Any] = None) -> MultiAgentDiagnosisResult:
        """
        执行多智能体协同诊断
        
        Args:
            symptoms: 症状描述
            sensor_data: 传感器数据
            context: 额外上下文
        
        Returns:
            MultiAgentDiagnosisResult: 诊断结果
        """
        import uuid
        
        diagnosis_id = f"MAD_{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"开始多智能体诊断: {diagnosis_id}")
        
        # 1. 并行收集各专家意见
        expert_tasks = [
            expert.analyze(symptoms, sensor_data, context)
            for expert in self.experts.values()
        ]
        
        expert_opinions = await asyncio.gather(*expert_tasks)
        
        # 2. 协调者整合意见
        final_conclusion = await self._coordinate_opinions(
            symptoms, expert_opinions
        )
        
        # 3. 生成模拟推演场景
        scenarios = await self._generate_scenarios(
            symptoms, final_conclusion, expert_opinions
        )
        
        # 4. 构建结果
        result = MultiAgentDiagnosisResult(
            diagnosis_id=diagnosis_id,
            symptoms=symptoms,
            final_conclusion=final_conclusion["conclusion"],
            confidence=final_conclusion["confidence"],
            consensus_level=final_conclusion["consensus_level"],
            expert_opinions=list(expert_opinions),
            dissenting_views=final_conclusion.get("dissenting_views", []),
            recommended_actions=final_conclusion["actions"],
            spare_parts=final_conclusion.get("spare_parts", []),
            related_cases=final_conclusion.get("related_cases", []),
            simulation_scenarios=scenarios
        )
        
        # 保存历史
        self._diagnosis_history.set(diagnosis_id, result)
        
        logger.info(f"多智能体诊断完成: {diagnosis_id}, 置信度: {result.confidence}")
        
        return result
    
    async def _coordinate_opinions(self, symptoms: str, 
                                  opinions: List[ExpertOpinion]) -> Dict[str, Any]:
        """协调专家意见"""
        # 统计各根因的置信度加权
        cause_confidence = {}
        all_suggestions = []
        all_evidence = []
        
        for op in opinions:
            cause = op.root_cause
            if cause not in cause_confidence:
                cause_confidence[cause] = {"confidence": 0, "count": 0, "experts": []}
            cause_confidence[cause]["confidence"] += op.confidence
            cause_confidence[cause]["count"] += 1
            cause_confidence[cause]["experts"].append(op.expert_name)
            
            all_suggestions.extend(op.suggestions)
            all_evidence.extend(op.evidence)
        
        # 找出最高置信度的根因
        best_cause = max(cause_confidence.items(), 
                        key=lambda x: x[1]["confidence"])
        
        # 计算共识程度
        total_opinions = len(opinions)
        consensus_count = best_cause[1]["count"]
        consensus_level = consensus_count / total_opinions
        
        # 收集不同意见
        dissenting_views = [
            op for op in opinions 
            if op.root_cause != best_cause[0]
        ]
        
        # 生成建议动作
        actions = self._prioritize_actions(all_suggestions)
        
        # 生成备件清单
        spare_parts = self._generate_spare_parts_list(best_cause[0], opinions)
        
        return {
            "conclusion": best_cause[0],
            "confidence": best_cause[1]["confidence"] / best_cause[1]["count"],
            "consensus_level": consensus_level,
            "supporting_experts": best_cause[1]["experts"],
            "dissenting_views": dissenting_views[:2],  # 最多保留2个不同意见
            "evidence": list(set(all_evidence))[:5],  # 去重，最多5条
            "actions": actions,
            "spare_parts": spare_parts,
            "related_cases": ["CASE_20230815_001", "CASE_20231022_003"]
        }
    
    def _prioritize_actions(self, suggestions: List[str]) -> List[Dict[str, Any]]:
        """优先排序建议动作"""
        # 简单的优先级判断
        priority_keywords = {
            "critical": ["立即", "马上", "紧急", "危险"],
            "high": ["尽快", "检查", "确认"],
            "medium": ["考虑", "评估", "优化"],
            "low": ["可以", "建议", "参考"]
        }
        
        prioritized = []
        for suggestion in suggestions:
            priority = "medium"
            for level, keywords in priority_keywords.items():
                if any(kw in suggestion for kw in keywords):
                    priority = level
                    break
            
            prioritized.append({
                "action": suggestion,
                "priority": priority,
                "estimated_time": self._estimate_time(suggestion),
                "requires_shutdown": "停机" in suggestion or "停电" in suggestion
            })
        
        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        prioritized.sort(key=lambda x: priority_order.get(x["priority"], 2))
        
        return prioritized[:10]  # 最多10条
    
    def _estimate_time(self, action: str) -> str:
        """估计操作时间"""
        if any(kw in action for kw in ["校准", "检查", "确认"]):
            return "30分钟-1小时"
        elif any(kw in action for kw in ["更换", "清洗", "维修"]):
            return "2-4小时"
        elif any(kw in action for kw in ["停机", "大修", "改造"]):
            return "1-3天"
        return "未知"
    
    def _generate_spare_parts_list(self, root_cause: str, 
                                   opinions: List[ExpertOpinion]) -> List[Dict[str, Any]]:
        """生成备件清单"""
        # 根据根因关键词匹配备件
        parts_mapping = {
            "曝气盘": [{"name": "微孔曝气盘", "spec": "Φ215mm", "quantity": 5}],
            "风机": [{"name": "风机滤网", "spec": "适配型号", "quantity": 2}],
            "轴承": [{"name": "深沟球轴承", "spec": "6205-2RS", "quantity": 2}],
            "机械密封": [{"name": "机械密封件", "spec": "适用泵型号", "quantity": 1}],
            "传感器": [{"name": "溶解氧传感器探头", "spec": "工业级", "quantity": 1}],
            "电机": [{"name": "电机绝缘漆", "spec": "H级", "quantity": 1}]
        }
        
        spare_parts = []
        for keyword, parts in parts_mapping.items():
            if keyword in root_cause:
                spare_parts.extend(parts)
        
        # 如果没有匹配到，给出通用建议
        if not spare_parts:
            spare_parts = [
                {"name": "常用紧固件包", "spec": "M6-M12", "quantity": 1},
                {"name": "密封胶带", "spec": "PTFE", "quantity": 2}
            ]
        
        return spare_parts
    
    async def _generate_scenarios(self, symptoms: str, conclusion: Dict[str, Any],
                                 opinions: List[ExpertOpinion]) -> List[Dict[str, Any]]:
        """生成模拟推演场景"""
        scenarios = [
            {
                "scenario": "及时处理",
                "description": "按照建议立即处理",
                "timeline": [
                    {"time": "0h", "action": "开始处理", "expected_state": "设备停机"},
                    {"time": "2h", "action": "完成维修", "expected_state": "设备就绪"},
                    {"time": "4h", "action": "恢复运行", "expected_state": "正常运行"}
                ],
                "outcome": "预计4小时内恢复正常",
                "risk_level": "low"
            },
            {
                "scenario": "延迟处理",
                "description": "延迟24小时处理",
                "timeline": [
                    {"time": "0h", "action": "维持现状", "expected_state": "带病运行"},
                    {"time": "12h", "action": "故障扩大", "expected_state": "参数恶化"},
                    {"time": "24h", "action": "被迫停机", "expected_state": "设备损坏风险"}
                ],
                "outcome": "可能导致二次损坏",
                "risk_level": "high"
            }
        ]
        return scenarios
    
    def get_diagnosis_history(self, limit: int = 10) -> List[MultiAgentDiagnosisResult]:
        """获取诊断历史"""
        history = []
        for key in list(self._diagnosis_history.keys())[-limit:]:
            result = self._diagnosis_history.get(key)
            if result:
                history.append(result)
        return history
