"""
知识库API路由

实现知识搜索、智能诊断等接口
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.api.dependencies import (
    get_current_user, require_permissions,
    UserContext
)

router = APIRouter(prefix="/knowledge", tags=["知识库"])


# Pydantic模型
class KnowledgeDoc(BaseModel):
    """知识文档"""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    similarity_score: Optional[float] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = None


class DiagnoseRequest(BaseModel):
    """诊断请求"""
    symptoms: str = Field(..., min_length=5)
    device_id: Optional[str] = None
    tags: Optional[Dict[str, float]] = None


class DiagnoseResponse(BaseModel):
    """诊断响应"""
    diagnosis_id: str
    root_cause: str
    confidence: float
    suggestions: List[str]
    spare_parts: List[Dict[str, Any]]
    references: List[KnowledgeDoc]


# 模拟知识库数据
_knowledge_base = {
    "DOC_001": {
        "id": "DOC_001",
        "title": "曝气池溶解氧异常处理",
        "content": """
当曝气池溶解氧浓度低于2mg/L时，可能的原因包括：
1. 曝气盘堵塞或损坏
2. 风机故障或风量不足
3. DO传感器需要校准
4. 进水负荷突然增加

处理措施：
1. 检查并清洗曝气盘
2. 检查风机运行状态
3. 校准DO传感器
4. 调整进水流量
        """,
        "category": "异常处理",
        "tags": ["曝气池", "溶解氧", "DO", "故障处理"]
    },
    "DOC_002": {
        "id": "DOC_002",
        "title": "污泥膨胀预防与控制",
        "content": """
污泥膨胀的主要症状：
- 污泥沉降性能差
- SVI值超过200
- 出水浑浊

预防措施：
1. 控制营养物质比例（BOD:N:P = 100:5:1）
2. 维持适当的溶解氧（2-4mg/L）
3. 控制污泥龄
4. 定期排泥

应急处理：
1. 投加絮凝剂
2. 调整曝气量
3. 加大排泥量
        """,
        "category": "工艺控制",
        "tags": ["污泥膨胀", "SVI", "沉降性", "工艺控制"]
    },
    "DOC_003": {
        "id": "DOC_003",
        "title": "泵类设备维护保养",
        "content": """
日常维护项目：
1. 检查轴承温度和振动
2. 检查密封是否泄漏
3. 检查电机电流
4. 清洁过滤器

定期保养（每月）：
1. 更换润滑油
2. 检查联轴器
3. 紧固螺栓

易损件清单：
- 机械密封
- 轴承
- 叶轮
- O型圈
        """,
        "category": "设备维护",
        "tags": ["泵", "机械密封", "轴承", "保养"]
    }
}


@router.post("/search", response_model=List[KnowledgeDoc])
async def search_knowledge(
    request: SearchRequest,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    搜索知识库
    
    使用关键词搜索相关知识文档
    """
    results = []
    
    # 简单的关键词匹配（实际应使用向量检索）
    query_lower = request.query.lower()
    query_keywords = set(query_lower.split())
    
    for doc_id, doc in _knowledge_base.items():
        # 分类过滤
        if request.category and doc["category"] != request.category:
            continue
        
        # 计算相似度（简化版）
        title_score = len(query_keywords & set(doc["title"].lower().split()))
        content_score = len(query_keywords & set(doc["content"].lower().split()))
        tag_score = sum(1 for tag in doc["tags"] if any(kw in tag.lower() for kw in query_keywords))
        
        total_score = (title_score * 3 + content_score + tag_score * 2) / 10
        
        if total_score > 0:
            results.append(KnowledgeDoc(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                category=doc["category"],
                tags=doc["tags"],
                similarity_score=round(min(total_score, 1.0), 2)
            ))
    
    # 按相似度排序
    results.sort(key=lambda x: x.similarity_score or 0, reverse=True)
    
    return results[:request.limit]


@router.get("/categories")
async def get_categories(
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取知识分类
    
    返回所有知识文档分类
    """
    categories = set()
    for doc in _knowledge_base.values():
        categories.add(doc["category"])
    
    return list(categories)


@router.get("/doc/{doc_id}", response_model=KnowledgeDoc)
async def get_document(
    doc_id: str,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取知识文档详情
    
    返回指定ID的知识文档完整内容
    """
    doc = _knowledge_base.get(doc_id)
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"文档 {doc_id} 不存在"
        )
    
    return KnowledgeDoc(
        id=doc["id"],
        title=doc["title"],
        content=doc["content"],
        category=doc["category"],
        tags=doc["tags"],
        similarity_score=1.0
    )


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    request: DiagnoseRequest,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    智能诊断
    
    基于症状描述进行故障诊断
    """
    import uuid
    
    # 分析症状关键词
    symptoms_lower = request.symptoms.lower()
    
    # 模拟诊断逻辑
    diagnosis_map = {
        "氧": {
            "root_cause": "曝气盘部分堵塞，导致曝气效率下降",
            "confidence": 0.85,
            "suggestions": [
                "检查并清洗曝气盘",
                "检查风机运行状态",
                "校准DO传感器"
            ],
            "spare_parts": [
                {"name": "曝气盘", "quantity": 5},
                {"name": "风机滤网", "quantity": 1}
            ],
            "references": ["DOC_001"]
        },
        "污泥": {
            "root_cause": "进水营养物质比例失调，导致污泥膨胀",
            "confidence": 0.78,
            "suggestions": [
                "检测进水BOD、N、P比例",
                "调整营养物质投加量",
                "适当加大排泥量",
                "考虑投加絮凝剂"
            ],
            "spare_parts": [
                {"name": "絮凝剂", "quantity": 50}
            ],
            "references": ["DOC_002"]
        },
        "泵": {
            "root_cause": "泵机械密封磨损导致泄漏",
            "confidence": 0.92,
            "suggestions": [
                "更换机械密封",
                "检查轴承状态",
                "检查联轴器对中"
            ],
            "spare_parts": [
                {"name": "机械密封", "quantity": 1},
                {"name": "轴承", "quantity": 2}
            ],
            "references": ["DOC_003"]
        }
    }
    
    # 匹配症状
    matched_diagnosis = None
    for keyword, diagnosis in diagnosis_map.items():
        if keyword in symptoms_lower:
            matched_diagnosis = diagnosis
            break
    
    # 如果没有匹配到，使用默认诊断
    if not matched_diagnosis:
        matched_diagnosis = {
            "root_cause": "根据症状无法确定具体原因，建议进一步检查相关设备",
            "confidence": 0.5,
            "suggestions": [
                "检查设备运行日志",
                "联系技术支持",
                "进行现场巡检"
            ],
            "spare_parts": [],
            "references": []
        }
    
    # 获取参考文档
    references = []
    for ref_id in matched_diagnosis["references"]:
        if ref_id in _knowledge_base:
            doc = _knowledge_base[ref_id]
            references.append(KnowledgeDoc(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"][:150] + "...",
                category=doc["category"],
                tags=doc["tags"],
                similarity_score=0.9
            ))
    
    return DiagnoseResponse(
        diagnosis_id=f"DIAG_{uuid.uuid4().hex[:12].upper()}",
        root_cause=matched_diagnosis["root_cause"],
        confidence=matched_diagnosis["confidence"],
        suggestions=matched_diagnosis["suggestions"],
        spare_parts=matched_diagnosis["spare_parts"],
        references=references
    )


@router.post("/feedback")
async def submit_feedback(
    diagnosis_id: str,
    helpful: bool,
    comment: Optional[str] = None,
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    提交诊断反馈
    
    对诊断结果进行反馈，用于改进诊断模型
    """
    # 实际应存储到数据库
    return {
        "success": True,
        "message": "感谢您的反馈",
        "data": {
            "diagnosis_id": diagnosis_id,
            "helpful": helpful,
            "recorded_at": "2024-01-15T10:30:00Z"
        }
    }


@router.get("/statistics")
async def get_knowledge_statistics(
    user: UserContext = Depends(require_permissions("data:read"))
):
    """
    获取知识库统计
    
    返回知识库使用统计信息
    """
    return {
        "total_documents": len(_knowledge_base),
        "categories": len(set(d["category"] for d in _knowledge_base.values())),
        "total_tags": len(set(tag for d in _knowledge_base.values() for tag in d["tags"])),
        "search_count_today": 156,
        "diagnosis_count_today": 23,
        "accuracy_rate": 0.87
    }
