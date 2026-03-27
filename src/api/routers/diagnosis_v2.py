"""
V2 诊断API - 多智能体协同诊断能力

增强版智能诊断接口
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user, require_permissions, UserContext
from src.diagnosis.multi_agent_diagnosis import (
    MultiAgentDiagnosisEngine, MultiAgentDiagnosisResult
)
from src.knowledge.graph_rag import graph_rag
from src.tasks.task_tracker import task_tracker, TaskPriority, TrackedTask
from src.agents.camel_integration import IndustrialDiagnosisSociety

router = APIRouter(prefix="/v2/diagnosis", tags=["智能诊断V2"])

# 诊断引擎实例
diagnosis_engine = MultiAgentDiagnosisEngine()
camel_society = IndustrialDiagnosisSociety()


class DiagnosisRequestV2(BaseModel):
    """V2诊断请求"""
    symptoms: str = Field(..., min_length=5, description="故障症状描述")
    device_id: Optional[str] = Field(None, description="相关设备ID")
    sensor_data: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="传感器数据"
    )
    use_multi_agent: bool = Field(True, description="是否使用多智能体诊断")
    use_graph_rag: bool = Field(True, description="是否使用知识图谱增强")
    use_camel: bool = Field(False, description="是否使用CAMEL社会协作")
    priority: str = Field("normal", pattern=r"^(critical|high|normal|low)$")


class DiagnosisResponseV2(BaseModel):
    """V2诊断响应"""
    diagnosis_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None


@router.post("/analyze", response_model=DiagnosisResponseV2)
async def analyze_v2(
    request: DiagnosisRequestV2,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    V2 智能诊断分析
    
    集成多智能体协同诊断、知识图谱增强
    """
    # 准备传感器数据
    sensor_data = request.sensor_data or {}
    
    # 构建上下文
    context = {
        "user_id": user.user_id,
        "device_id": request.device_id,
        "use_graph_rag": request.use_graph_rag
    }
    
    # 如果使用CAMEL社会协作
    if request.use_camel:
        task = task_tracker.create_task(
            task_type="camel_diagnosis",
            description=f"CAMEL协作诊断: {request.symptoms[:50]}...",
            priority=TaskPriority[request.priority.upper()],
            metadata={"user_id": user.user_id}
        )
        
        # 异步执行CAMEL诊断
        background_tasks.add_task(
            _execute_camel_diagnosis,
            task,
            request.symptoms,
            sensor_data
        )
        
        return DiagnosisResponseV2(
            diagnosis_id=task.task_id,
            status="processing",
            message="CAMEL协作诊断已启动，请查询任务状态获取结果",
            task_id=task.task_id
        )
    
    # 标准多智能体诊断
    if request.use_multi_agent:
        result = await diagnosis_engine.diagnose(
            symptoms=request.symptoms,
            sensor_data=sensor_data,
            context=context
        )
        
        return DiagnosisResponseV2(
            diagnosis_id=result.diagnosis_id,
            status="completed",
            message="多智能体诊断完成",
            result=result.to_dict()
        )
    
    # 简化版诊断
    return DiagnosisResponseV2(
        diagnosis_id="SIMPLE_001",
        status="completed",
        message="标准诊断完成",
        result={"symptoms": request.symptoms}
    )


async def _execute_camel_diagnosis(task: TrackedTask, symptoms: str, sensor_data: Dict):
    """后台执行CAMEL诊断"""
    async def diagnosis_work(task: TrackedTask):
        # 更新进度
        task_tracker.update_progress(
            task.task_id,
            step=1,
            action="初始化CAMEL社会...",
            percentage=10
        )
        
        # 执行诊断
        result = await camel_society.diagnose(symptoms, sensor_data)
        
        # 更新进度
        task_tracker.update_progress(
            task.task_id,
            step=5,
            action="诊断完成",
            percentage=100
        )
        
        return result
    
    await task_tracker.execute(task, diagnosis_work)


@router.get("/task/{task_id}")
async def get_diagnosis_task(
    task_id: str,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取诊断任务状态
    
    查询异步诊断任务的进度和结果
    """
    task = task_tracker.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "progress": task.progress.to_dict(),
        "result": task.result,
        "error": task.error,
        "duration_seconds": task.duration_seconds()
    }


@router.post("/knowledge/query")
async def query_knowledge_graph(
    query: str,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    知识图谱查询
    
    使用GraphRAG检索工业知识
    """
    result = await graph_rag.query(query)
    
    return result


@router.get("/knowledge/graph")
async def get_knowledge_graph(
    entity_id: Optional[str] = None,
    depth: int = 2,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取知识图谱
    
    返回知识图谱的子图或完整图谱
    """
    if entity_id:
        # 获取实体周围的子图
        subgraph = graph_rag.kg.subgraph_query(entity_id, depth)
        return subgraph
    else:
        # 返回统计信息
        return graph_rag.kg.to_dict()


@router.get("/history")
async def get_diagnosis_history(
    limit: int = 10,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取诊断历史
    
    返回最近的多智能体诊断记录
    """
    history = diagnosis_engine.get_diagnosis_history(limit)
    
    return {
        "total": len(history),
        "history": [h.to_dict() for h in history]
    }


@router.get("/experts")
async def get_expert_agents(
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取专家智能体列表
    
    返回可用的诊断专家及其能力
    """
    experts = [
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
    
    return {
        "total": len(experts),
        "experts": experts
    }


@router.get("/society/status")
async def get_camel_society_status(
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取CAMEL社会状态
    
    返回多智能体社会的运行状态
    """
    return camel_society.get_society_status()


@router.get("/tasks/stats")
async def get_task_statistics(
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取任务统计
    
    返回诊断任务的整体统计
    """
    return task_tracker.get_stats()
