"""
CAMEL-AI 框架集成

多智能体协调与通信框架
"""

from typing import List, Dict, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json

from src.utils.structured_logging import get_logger

logger = get_logger("camel_integration")


class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGNMENT = "task_assignment"
    OPINION = "opinion"
    QUESTION = "question"
    ANSWER = "answer"
    DEBATE = "debate"
    CONSENSUS = "consensus"
    SYSTEM = "system"


class AgentRole(Enum):
    """智能体角色"""
    WORKER = "worker"          # 执行者
    CRITIC = "critic"          # 批评者
    COORDINATOR = "coordinator"  # 协调者
    EXPERT = "expert"          # 专家
    OBSERVER = "observer"      # 观察者


@dataclass
class AgentMessage:
    """智能体消息"""
    message_id: str
    sender_id: str
    receiver_id: Optional[str]  # None表示广播
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Task:
    """任务定义"""
    task_id: str
    description: str
    task_type: str
    assigned_agents: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    sub_tasks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "task_type": self.task_type,
            "assigned_agents": self.assigned_agents,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_task_id": self.parent_task_id,
            "sub_tasks": self.sub_tasks
        }


class CamelAgent:
    """
    CAMEL框架智能体基类
    
    支持角色扮演、记忆管理和消息通信
    """
    
    def __init__(self, agent_id: str, name: str, role: AgentRole,
                 system_message: str, capabilities: List[str] = None):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_message = system_message
        self.capabilities = capabilities or []
        
        # 状态
        self.memory: List[AgentMessage] = []
        self.task_history: List[str] = []
        self.is_busy = False
        
        # 通信回调
        self._message_handler: Optional[Callable[[AgentMessage], None]] = None
        
        logger.info(f"智能体创建: {name} ({agent_id}) - 角色: {role.value}")
    
    def set_message_handler(self, handler: Callable[[AgentMessage], None]):
        """设置消息处理器"""
        self._message_handler = handler
    
    def receive_message(self, message: AgentMessage):
        """接收消息"""
        self.memory.append(message)
        
        # 触发处理
        if self._message_handler:
            self._message_handler(message)
        
        logger.debug(f"{self.name} 收到消息: {message.message_type.value}")
    
    async def send_message(self, content: str, message_type: MessageType,
                          receiver_id: Optional[str] = None,
                          metadata: Dict[str, Any] = None) -> AgentMessage:
        """发送消息"""
        import uuid
        
        message = AgentMessage(
            message_id=f"MSG_{uuid.uuid4().hex[:8].upper()}",
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {}
        )
        
        return message
    
    async def execute_task(self, task: Task) -> Any:
        """执行任务（子类应重写）"""
        self.is_busy = True
        self.task_history.append(task.task_id)
        
        try:
            logger.info(f"{self.name} 执行任务: {task.task_id}")
            
            # 模拟任务执行
            await asyncio.sleep(0.5)
            
            result = {
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "task_id": task.task_id,
                "status": "completed",
                "output": f"由 {self.name} 完成的分析结果",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.utcnow()
            
            return result
            
        finally:
            self.is_busy = False
    
    def get_context_window(self, limit: int = 10) -> List[AgentMessage]:
        """获取上下文窗口"""
        return self.memory[-limit:]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "is_busy": self.is_busy,
            "task_count": len(self.task_history)
        }


class CamelSociety:
    """
    CAMEL社会/组织
    
    管理多个智能体的协作
    """
    
    def __init__(self, society_id: str, name: str, description: str = ""):
        self.society_id = society_id
        self.name = name
        self.description = description
        
        self.agents: Dict[str, CamelAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.message_bus: List[AgentMessage] = []
        
        # 协作配置
        self.collaboration_mode = "sequential"  # sequential, parallel, debate
        self.max_rounds = 3
        
        logger.info(f"CAMEL社会创建: {name} ({society_id})")
    
    def register_agent(self, agent: CamelAgent):
        """注册智能体"""
        agent.set_message_handler(self._route_message)
        self.agents[agent.agent_id] = agent
        logger.info(f"智能体 {agent.name} 已注册到社会 {self.name}")
    
    def _route_message(self, message: AgentMessage):
        """路由消息到目标智能体"""
        self.message_bus.append(message)
        
        if message.receiver_id:
            # 定向消息
            target = self.agents.get(message.receiver_id)
            if target:
                target.receive_message(message)
        else:
            # 广播消息
            for agent in self.agents.values():
                if agent.agent_id != message.sender_id:
                    agent.receive_message(message)
    
    async def create_task(self, description: str, task_type: str,
                         agent_ids: Optional[List[str]] = None) -> Task:
        """创建任务"""
        import uuid
        
        task_id = f"TASK_{uuid.uuid4().hex[:8].upper()}"
        
        # 如果没有指定智能体，分配给所有空闲智能体
        if not agent_ids:
            agent_ids = [aid for aid, agent in self.agents.items() if not agent.is_busy]
        
        task = Task(
            task_id=task_id,
            description=description,
            task_type=task_type,
            assigned_agents=agent_ids
        )
        
        self.tasks[task_id] = task
        logger.info(f"任务创建: {task_id} - {description}")
        
        return task
    
    async def execute_collaborative_task(self, task: Task,
                                        mode: str = "parallel") -> Dict[str, Any]:
        """
        执行协作任务
        
        Args:
            task: 任务对象
            mode: 协作模式 (sequential/parallel/debate)
        
        Returns:
            协作结果
        """
        logger.info(f"开始协作任务: {task.task_id} 模式: {mode}")
        
        if mode == "parallel":
            return await self._execute_parallel(task)
        elif mode == "sequential":
            return await self._execute_sequential(task)
        elif mode == "debate":
            return await self._execute_debate(task)
        else:
            raise ValueError(f"未知协作模式: {mode}")
    
    async def _execute_parallel(self, task: Task) -> Dict[str, Any]:
        """并行执行"""
        task.status = "in_progress"
        
        # 并行分配给多个智能体
        agent_tasks = []
        for agent_id in task.assigned_agents:
            agent = self.agents.get(agent_id)
            if agent:
                agent_tasks.append(agent.execute_task(task))
        
        # 等待所有结果
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # 整合结果
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        task.status = "completed"
        task.result = {
            "mode": "parallel",
            "total_agents": len(agent_tasks),
            "successful": len(successful_results),
            "results": successful_results
        }
        
        return task.result
    
    async def _execute_sequential(self, task: Task) -> Dict[str, Any]:
        """顺序执行"""
        task.status = "in_progress"
        
        results = []
        context = ""
        
        for agent_id in task.assigned_agents:
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            
            # 添加上下文到任务描述
            task_with_context = Task(
                task_id=task.task_id,
                description=f"{task.description}\n前置结果: {context}",
                task_type=task.task_type
            )
            
            result = await agent.execute_task(task_with_context)
            results.append(result)
            
            # 更新上下文
            context = str(result.get("output", ""))[:200]
        
        task.status = "completed"
        task.result = {
            "mode": "sequential",
            "steps": len(results),
            "results": results
        }
        
        return task.result
    
    async def _execute_debate(self, task: Task) -> Dict[str, Any]:
        """
        辩论模式执行
        
        智能体之间进行多轮讨论达成共识
        """
        task.status = "in_progress"
        
        opinions = []
        
        # 第一轮：各智能体发表观点
        for agent_id in task.assigned_agents:
            agent = self.agents.get(agent_id)
            if agent:
                result = await agent.execute_task(task)
                
                # 发送观点消息
                message = await agent.send_message(
                    content=result.get("output", ""),
                    message_type=MessageType.OPINION,
                    metadata={"round": 1, "task_id": task.task_id}
                )
                self._route_message(message)
                
                opinions.append({
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "opinion": result
                })
        
        # 后续轮次：讨论与反驳
        for round_num in range(2, self.max_rounds + 1):
            for agent_id in task.assigned_agents:
                agent = self.agents.get(agent_id)
                if not agent:
                    continue
                
                # 获取其他智能体的观点
                other_opinions = [o for o in opinions if o["agent_id"] != agent_id]
                
                if other_opinions:
                    # 生成反驳或支持意见
                    debate_content = f"针对{other_opinions[0]['agent_name']}的观点："
                    
                    message = await agent.send_message(
                        content=debate_content,
                        message_type=MessageType.DEBATE,
                        metadata={"round": round_num, "task_id": task.task_id}
                    )
                    self._route_message(message)
        
        task.status = "completed"
        task.result = {
            "mode": "debate",
            "rounds": self.max_rounds,
            "opinions": opinions,
            "message_count": len(self.message_bus)
        }
        
        return task.result
    
    def get_society_status(self) -> Dict[str, Any]:
        """获取社会状态"""
        return {
            "society_id": self.society_id,
            "name": self.name,
            "agent_count": len(self.agents),
            "task_count": len(self.tasks),
            "active_tasks": sum(1 for t in self.tasks.values() if t.status == "in_progress"),
            "agents": [a.to_dict() for a in self.agents.values()],
            "recent_messages": len(self.message_bus)
        }


class IndustrialDiagnosisSociety(CamelSociety):
    """
    工业诊断专用CAMEL社会
    
    预配置工业诊断专家智能体
    """
    
    def __init__(self):
        super().__init__(
            society_id="industrial_diagnosis_001",
            name="工业故障诊断专家委员会",
            description="多领域专家协作诊断工业设备故障"
        )
        
        self._init_expert_agents()
    
    def _init_expert_agents(self):
        """初始化专家智能体"""
        experts = [
            {
                "id": "EXP_MECH_001",
                "name": "机械专家",
                "role": AgentRole.EXPERT,
                "system": "你是机械设备诊断专家，精通振动分析和磨损诊断。",
                "capabilities": ["振动分析", "轴承诊断", "动平衡"]
            },
            {
                "id": "EXP_ELEC_001",
                "name": "电气专家",
                "role": AgentRole.EXPERT,
                "system": "你是电气系统专家，精通电机和控制系统诊断。",
                "capabilities": ["电机诊断", "绝缘测试", "变频控制"]
            },
            {
                "id": "EXP_PROC_001",
                "name": "工艺专家",
                "role": AgentRole.EXPERT,
                "system": "你是污水处理工艺专家，精通活性污泥法工艺控制。",
                "capabilities": ["工艺优化", "参数调节", "水质分析"]
            },
            {
                "id": "CRITIC_001",
                "name": "诊断评论家",
                "role": AgentRole.CRITIC,
                "system": "你是诊断质量评论家，负责评估诊断结论的合理性。",
                "capabilities": ["逻辑验证", "风险评估", "方案优化"]
            },
            {
                "id": "COORD_001",
                "name": "诊断协调员",
                "role": AgentRole.COORDINATOR,
                "system": "你是诊断协调员，负责整合各专家意见形成最终结论。",
                "capabilities": ["意见整合", "冲突解决", "报告生成"]
            }
        ]
        
        for expert_config in experts:
            agent = CamelAgent(
                agent_id=expert_config["id"],
                name=expert_config["name"],
                role=expert_config["role"],
                system_message=expert_config["system"],
                capabilities=expert_config["capabilities"]
            )
            self.register_agent(agent)
    
    async def diagnose(self, symptoms: str, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行诊断任务
        
        Args:
            symptoms: 症状描述
            sensor_data: 传感器数据
        
        Returns:
            诊断结果
        """
        # 创建诊断任务
        task = await self.create_task(
            description=f"诊断故障: {symptoms}",
            task_type="fault_diagnosis"
        )
        
        # 使用辩论模式进行诊断
        result = await self.execute_collaborative_task(task, mode="debate")
        
        return {
            "diagnosis_id": task.task_id,
            "symptoms": symptoms,
            "collaboration_result": result,
            "expert_count": len(self.agents),
            "society": self.name
        }


# 使用示例
async def demo_camel_society():
    """演示CAMEL社会"""
    society = IndustrialDiagnosisSociety()
    
    # 执行诊断
    result = await society.diagnose(
        symptoms="曝气池溶解氧持续偏低，风机噪音异常",
        sensor_data={"do": 1.5, "vibration": 8.5, "current": 25.3}
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(demo_camel_society())
