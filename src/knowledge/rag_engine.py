"""
RAG 检索增强生成引擎
用于工业故障诊断和知识问答
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger


class RAGEngine:
    """RAG 引擎 - 检索增强生成"""
    
    def __init__(self, knowledge_dir: str = "data/knowledge_base", config: Optional[Dict[str, Any]] = None):
        """
        初始化 RAG 引擎
        
        Args:
            knowledge_dir: 知识库文档目录
            config: 配置参数
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.config = config or {}
        
        self.vector_store = None
        self.is_initialized = False
        
        logger.info(f"RAGEngine 初始化完成，知识库目录：{knowledge_dir}")
    
    def initialize(self):
        """初始化向量数据库"""
        try:
            from .vector_store import VectorStore
            from .document_loader import DocumentLoader
            
            # 加载文档
            loader = DocumentLoader(self.knowledge_dir)
            documents = loader.load()
            
            if not documents:
                logger.warning("知识库为空，请先添加文档")
                return
            
            # 构建向量库
            self.vector_store = VectorStore()
            self.vector_store.add_documents(documents)
            
            self.is_initialized = True
            logger.info(f"RAG 引擎初始化完成，共 {len(documents)} 个文档片段")
            
        except Exception as e:
            logger.error(f"RAG 引擎初始化失败：{e}")
    
    def query(self, question: str, k: int = 3) -> Dict[str, Any]:
        """
        查询知识库
        
        Args:
            question: 问题
            k: 返回相关文档数量
            
        Returns:
            包含答案和参考文档的字典
        """
        if not self.is_initialized:
            self.initialize()
        
        if not self.vector_store:
            return {
                'answer': '知识库尚未初始化',
                'sources': []
            }
        
        # 检索相关文档
        relevant_docs = self.vector_store.similarity_search(question, k=k)
        
        # 构建上下文
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # 调用 LLM 生成答案 (这里使用占位符，实际应调用 LLM)
        answer = self._generate_answer(question, context)
        
        # 整理来源
        sources = [
            {
                'source': doc.metadata.get('source', 'unknown'),
                'page': doc.metadata.get('page', ''),
                'snippet': doc.page_content[:200] + '...'
            }
            for doc in relevant_docs
        ]
        
        return {
            'question': question,
            'answer': answer,
            'sources': sources,
            'context': context
        }
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        生成答案
        
        实际应用中应调用 LLM (如 Qwen, ChatGLM 等)
        这里使用简单模板作为示例
        """
        answer_template = f"""根据知识库中的相关信息，针对您的问题：

**问题**: {question}

**分析**: 
基于以下参考资料：
{context[:500]}...

**建议**:
1. 请检查相关设备运行状态
2. 参考操作规程进行处置
3. 如情况持续，请联系专业技术人员

*注：此为系统自动生成的建议，仅供参考*
"""
        return answer_template
    
    def add_document(self, file_path: str):
        """添加新文档到知识库"""
        if not self.is_initialized:
            self.initialize()
        
        from .document_loader import DocumentLoader
        
        loader = DocumentLoader(Path(file_path))
        documents = loader.load()
        
        if documents and self.vector_store:
            self.vector_store.add_documents(documents)
            logger.info(f"已添加文档：{file_path} ({len(documents)} 个片段)")
    
    def rebuild(self):
        """重建知识库"""
        logger.info("开始重建知识库...")
        self.vector_store = None
        self.is_initialized = False
        self.initialize()


# 使用示例
if __name__ == "__main__":
    rag = RAGEngine(knowledge_dir='data/knowledge_base')
    
    # 测试查询
    result = rag.query("DO 突然下降怎么办？")
    
    print(f"\n问题：{result['question']}")
    print(f"\n答案:\n{result['answer']}")
    print(f"\n参考来源:")
    for source in result['sources']:
        print(f"  - {source['source']}")
