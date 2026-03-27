"""
文档分块模块

功能需求: K-02 文档分块 - 智能分块策略
作者: ML Team
"""

import re
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import hashlib
from loguru import logger


class ChunkingStrategy(Enum):
    """分块策略"""
    FIXED_SIZE = "fixed_size"           # 固定大小
    RECURSIVE = "recursive"             # 递归分块
    SEMANTIC = "semantic"               # 语义分块
    PARAGRAPH = "paragraph"             # 段落分块
    MARKDOWN = "markdown"               # Markdown分块
    CODE = "code"                       # 代码分块


@dataclass
class Chunk:
    """文本块"""
    content: str
    index: int
    metadata: Dict
    chunk_id: str
    parent_doc: str


class DocumentChunker:
    """
    文档分块器
    
    支持多种分块策略：
    1. 固定大小分块 - 按字符/Token数分块
    2. 递归分块 - 按分隔符层级递归
    3. 语义分块 - 按语义边界分块
    4. 段落分块 - 按段落边界分块
    """
    
    def __init__(self, 
                 chunk_size: int = 500,
                 chunk_overlap: int = 50,
                 strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE):
        """
        初始化分块器
        
        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块间重叠大小
            strategy: 分块策略
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        
        logger.info(f"文档分块器初始化: strategy={strategy.value}, size={chunk_size}")
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        分块入口
        
        Args:
            text: 原始文本
            metadata: 元数据
            
        Returns:
            文本块列表
        """
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text, metadata)
        elif self.strategy == ChunkingStrategy.RECURSIVE:
            return self._chunk_recursive(text, metadata)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(text, metadata)
        elif self.strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_paragraph(text, metadata)
        elif self.strategy == ChunkingStrategy.MARKDOWN:
            return self._chunk_markdown(text, metadata)
        else:
            return self._chunk_recursive(text, metadata)
    
    def _chunk_fixed_size(self, text: str, metadata: Optional[Dict]) -> List[Chunk]:
        """固定大小分块"""
        chunks = []
        parent_doc = metadata.get('source', 'unknown') if metadata else 'unknown'
        
        start = 0
        index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # 生成唯一ID
            chunk_id = hashlib.md5(f"{parent_doc}_{index}_{chunk_text[:50]}".encode()).hexdigest()[:16]
            
            chunk = Chunk(
                content=chunk_text,
                index=index,
                metadata={
                    'start_char': start,
                    'end_char': end,
                    'char_count': len(chunk_text),
                    **(metadata or {})
                },
                chunk_id=chunk_id,
                parent_doc=parent_doc
            )
            chunks.append(chunk)
            
            # 移动窗口，考虑重叠
            start = end - self.chunk_overlap
            index += 1
        
        return chunks
    
    def _chunk_recursive(self, text: str, metadata: Optional[Dict]) -> List[Chunk]:
        """
        递归分块
        
        按分隔符优先级递归分割：
        1. 段落分隔符 (\n\n)
        2. 换行符 (\n)
        3. 句子结束符 (.!?。！？)
        4. 空格
        5. 字符
        """
        separators = ['\n\n', '\n', '。', '！', '？', '. ', '! ', '? ', ' ', '']
        parent_doc = metadata.get('source', 'unknown') if metadata else 'unknown'
        
        chunks = []
        index = 0
        
        def recursive_split(text: str, sep_index: int = 0) -> List[str]:
            """递归分割"""
            if sep_index >= len(separators):
                return [text] if text else []
            
            separator = separators[sep_index]
            
            if not separator:
                # 最后一个级别：按字符分割
                return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]
            
            parts = text.split(separator)
            
            result = []
            current_chunk = ""
            
            for part in parts:
                candidate = current_chunk + separator + part if current_chunk else part
                
                if len(candidate) <= self.chunk_size:
                    current_chunk = candidate
                else:
                    if current_chunk:
                        # 当前块已满，保存并递归处理
                        if len(current_chunk) > self.chunk_size:
                            result.extend(recursive_split(current_chunk, sep_index + 1))
                        else:
                            result.append(current_chunk)
                    current_chunk = part
            
            if current_chunk:
                if len(current_chunk) > self.chunk_size:
                    result.extend(recursive_split(current_chunk, sep_index + 1))
                else:
                    result.append(current_chunk)
            
            return result
        
        split_texts = recursive_split(text)
        
        # 添加重叠
        for i, chunk_text in enumerate(split_texts):
            if i > 0 and self.chunk_overlap > 0:
                # 从前一块末尾取重叠部分
                prev_text = split_texts[i-1]
                overlap_text = prev_text[-self.chunk_overlap:]
                chunk_text = overlap_text + chunk_text
            
            chunk_id = hashlib.md5(f"{parent_doc}_{i}_{chunk_text[:50]}".encode()).hexdigest()[:16]
            
            chunk = Chunk(
                content=chunk_text,
                index=i,
                metadata={
                    'total_chunks': len(split_texts),
                    'char_count': len(chunk_text),
                    **(metadata or {})
                },
                chunk_id=chunk_id,
                parent_doc=parent_doc
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_semantic(self, text: str, metadata: Optional[Dict]) -> List[Chunk]:
        """
        语义分块
        
        基于句子边界和主题连贯性分块
        """
        # 句子分割正则
        sentence_pattern = r'[^。！？.!?]+[。！？.!?]+'
        sentences = re.findall(sentence_pattern, text)
        
        if not sentences:
            return self._chunk_recursive(text, metadata)
        
        parent_doc = metadata.get('source', 'unknown') if metadata else 'unknown'
        chunks = []
        current_chunk = []
        current_size = 0
        index = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # 如果当前块加上这个句子超过大小限制
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # 保存当前块
                chunk_text = ''.join(current_chunk)
                chunk_id = hashlib.md5(f"{parent_doc}_{index}_{chunk_text[:50]}".encode()).hexdigest()[:16]
                
                chunks.append(Chunk(
                    content=chunk_text,
                    index=index,
                    metadata={
                        'sentences': len(current_chunk),
                        'char_count': len(chunk_text),
                        **(metadata or {})
                    },
                    chunk_id=chunk_id,
                    parent_doc=parent_doc
                ))
                
                # 保留部分句子作为重叠
                overlap_sentences = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk[-1:]
                current_chunk = overlap_sentences
                current_size = sum(len(s) for s in current_chunk)
                index += 1
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # 处理剩余的句子
        if current_chunk:
            chunk_text = ''.join(current_chunk)
            chunk_id = hashlib.md5(f"{parent_doc}_{index}_{chunk_text[:50]}".encode()).hexdigest()[:16]
            
            chunks.append(Chunk(
                content=chunk_text,
                index=index,
                metadata={
                    'sentences': len(current_chunk),
                    'char_count': len(chunk_text),
                    **(metadata or {})
                },
                chunk_id=chunk_id,
                parent_doc=parent_doc
            ))
        
        return chunks
    
    def _chunk_paragraph(self, text: str, metadata: Optional[Dict]) -> List[Chunk]:
        """段落分块"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        parent_doc = metadata.get('source', 'unknown') if metadata else 'unknown'
        chunks = []
        
        for i, para in enumerate(paragraphs):
            chunk_id = hashlib.md5(f"{parent_doc}_{i}_{para[:50]}".encode()).hexdigest()[:16]
            
            chunk = Chunk(
                content=para,
                index=i,
                metadata={
                    'paragraph_index': i,
                    'total_paragraphs': len(paragraphs),
                    'char_count': len(para),
                    **(metadata or {})
                },
                chunk_id=chunk_id,
                parent_doc=parent_doc
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_markdown(self, text: str, metadata: Optional[Dict]) -> List[Chunk]:
        """Markdown分块 - 按标题层级分块"""
        # 匹配Markdown标题
        heading_pattern = r'^(#{1,6}\s.+)$'
        lines = text.split('\n')
        
        parent_doc = metadata.get('source', 'unknown') if metadata else 'unknown'
        chunks = []
        current_section = []
        current_heading = ""
        index = 0
        
        for line in lines:
            if re.match(heading_pattern, line):
                # 保存上一节
                if current_section:
                    section_text = '\n'.join(current_section)
                    chunk_id = hashlib.md5(f"{parent_doc}_{index}_{section_text[:50]}".encode()).hexdigest()[:16]
                    
                    chunks.append(Chunk(
                        content=section_text,
                        index=index,
                        metadata={
                            'heading': current_heading,
                            'section_index': index,
                            'char_count': len(section_text),
                            **(metadata or {})
                        },
                        chunk_id=chunk_id,
                        parent_doc=parent_doc
                    ))
                    index += 1
                
                current_heading = line
                current_section = [line]
            else:
                current_section.append(line)
        
        # 保存最后一节
        if current_section:
            section_text = '\n'.join(current_section)
            chunk_id = hashlib.md5(f"{parent_doc}_{index}_{section_text[:50]}".encode()).hexdigest()[:16]
            
            chunks.append(Chunk(
                content=section_text,
                index=index,
                metadata={
                    'heading': current_heading,
                    'section_index': index,
                    'char_count': len(section_text),
                    **(metadata or {})
                },
                chunk_id=chunk_id,
                parent_doc=parent_doc
            ))
        
        return chunks


class SmartChunker:
    """
    智能分块器
    
    根据文档类型自动选择最佳分块策略
    """
    
    def __init__(self):
        self.chunkers = {
            'pdf': DocumentChunker(strategy=ChunkingStrategy.RECURSIVE, chunk_size=500),
            'word': DocumentChunker(strategy=ChunkingStrategy.PARAGRAPH, chunk_size=800),
            'excel': DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=300),
            'markdown': DocumentChunker(strategy=ChunkingStrategy.MARKDOWN, chunk_size=600),
            'text': DocumentChunker(strategy=ChunkingStrategy.SEMANTIC, chunk_size=500)
        }
    
    def chunk_document(self, doc_type: str, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """智能分块"""
        chunker = self.chunkers.get(doc_type, self.chunkers['text'])
        return chunker.chunk(text, metadata)


# 使用示例
if __name__ == "__main__":
    # 测试文本
    test_text = """
# 第一章 概述

这是第一章的内容。工业智能监控系统的概述部分。
包含了系统的基本介绍和主要功能。

## 1.1 系统架构

系统采用分层架构设计。
包括数据采集层、存储层、分析层和应用层。

## 1.2 核心功能

核心功能包括：
1. 实时数据采集
2. 异常检测
3. 故障诊断

# 第二章 详细设计

详细设计部分包含具体的技术实现。
"""
    
    # 测试不同策略
    for strategy in ChunkingStrategy:
        print(f"\n{'='*50}")
        print(f"策略: {strategy.value}")
        print('='*50)
        
        chunker = DocumentChunker(strategy=strategy, chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk(test_text, {'source': 'test.md'})
        
        print(f"生成 {len(chunks)} 个块")
        for chunk in chunks[:3]:
            print(f"\n块 {chunk.index} (ID: {chunk.chunk_id}):")
            print(f"内容: {chunk.content[:80]}...")
