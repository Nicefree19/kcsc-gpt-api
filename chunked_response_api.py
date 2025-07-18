"""
대용량 문서를 위한 청크 기반 스트리밍 API
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
import os
from typing import Iterator, Dict, Any

class ChunkedDocumentProcessor:
    """대용량 문서를 청크로 분할하여 스트리밍"""
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size  # 토큰 단위
        
    def estimate_tokens(self, text: str) -> int:
        """간단한 토큰 추정"""
        korean_chars = len([c for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3])
        other_chars = len(text) - korean_chars
        return korean_chars * 2 + other_chars
    
    def chunk_document(self, content: str, chunk_tokens: int = 1000) -> Iterator[Dict[str, Any]]:
        """문서를 토큰 크기별로 청크 분할"""
        # 문단 단위로 분할
        paragraphs = content.split('\n\n')
        
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)
            
            # 현재 청크에 추가 가능한 경우
            if current_tokens + para_tokens <= chunk_tokens:
                current_chunk.append(para)
                current_tokens += para_tokens
            else:
                # 현재 청크 반환
                if current_chunk:
                    yield {
                        'chunk_index': chunk_index,
                        'content': '\n\n'.join(current_chunk),
                        'tokens': current_tokens,
                        'has_more': True
                    }
                    chunk_index += 1
                
                # 새 청크 시작
                current_chunk = [para]
                current_tokens = para_tokens
        
        # 마지막 청크
        if current_chunk:
            yield {
                'chunk_index': chunk_index,
                'content': '\n\n'.join(current_chunk),
                'tokens': current_tokens,
                'has_more': False
            }
    
    def create_smart_chunks(self, doc: Dict[str, Any], query: str = None) -> Iterator[Dict[str, Any]]:
        """쿼리 기반 스마트 청킹"""
        content = doc.get('content', '')
        
        if query:
            # 쿼리 관련 섹션 우선 추출
            relevant_sections = self._find_relevant_sections(content, query)
            for i, section in enumerate(relevant_sections):
                yield {
                    'chunk_index': i,
                    'relevance': 'high',
                    'content': section['content'],
                    'tokens': section['tokens'],
                    'section_title': section.get('title', ''),
                    'has_more': i < len(relevant_sections) - 1
                }
        else:
            # 일반 청킹
            yield from self.chunk_document(content)
    
    def _find_relevant_sections(self, content: str, query: str) -> list:
        """쿼리 관련 섹션 찾기"""
        sections = []
        query_lower = query.lower()
        
        # 섹션별 분할 (간단한 예시)
        parts = content.split('\n# ')  # 마크다운 헤더 기준
        
        for part in parts:
            if any(keyword in part.lower() for keyword in query_lower.split()):
                sections.append({
                    'content': part[:2000],  # 최대 2000자
                    'tokens': self.estimate_tokens(part[:2000]),
                    'title': part.split('\n')[0][:50]
                })
        
        return sections[:5]  # 최대 5개 섹션

# API 엔드포인트 추가
def add_chunked_endpoints(app: FastAPI):
    """기존 앱에 청크 엔드포인트 추가"""
    
    processor = ChunkedDocumentProcessor()
    
    @app.get("/api/v2/standard/{code}/chunked")
    async def get_chunked_document(
        code: str,
        chunk_size: int = Query(1000, description="청크당 최대 토큰"),
        query: Optional[str] = Query(None, description="검색 쿼리 (관련 부분 우선)"),
        start_chunk: int = Query(0, description="시작 청크 인덱스")
    ):
        """대용량 문서를 청크 단위로 반환"""
        # 문서 로드
        doc_path = f"standards_split/KDS/{code.replace(' ', '_')}_full.json"
        if not os.path.exists(doc_path):
            raise HTTPException(404, f"Document {code} not found")
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        # 청크 생성
        chunks = list(processor.create_smart_chunks(doc, query))
        
        # 페이지네이션
        if start_chunk >= len(chunks):
            return {
                "code": code,
                "total_chunks": len(chunks),
                "chunks": [],
                "completed": True
            }
        
        # 현재 페이지 청크
        page_chunks = chunks[start_chunk:start_chunk + 3]  # 한번에 3개까지
        
        return {
            "code": code,
            "query": query,
            "total_chunks": len(chunks),
            "current_chunk": start_chunk,
            "chunks": page_chunks,
            "next_chunk": start_chunk + len(page_chunks) if start_chunk + len(page_chunks) < len(chunks) else None,
            "completed": start_chunk + len(page_chunks) >= len(chunks)
        }
    
    @app.get("/api/v2/standard/{code}/stream")
    async def stream_document(
        code: str,
        chunk_tokens: int = Query(500, description="청크당 토큰")
    ):
        """문서를 스트리밍으로 반환"""
        doc_path = f"standards_split/KDS/{code.replace(' ', '_')}_full.json"
        if not os.path.exists(doc_path):
            raise HTTPException(404, f"Document {code} not found")
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        def generate():
            """스트리밍 생성기"""
            for chunk in processor.chunk_document(doc.get('content', ''), chunk_tokens):
                yield json.dumps(chunk, ensure_ascii=False) + "\n"
        
        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson"
        )
    
    @app.post("/api/v2/search/relevant-chunks")
    async def search_relevant_chunks(
        code: str,
        keywords: List[str],
        max_chunks: int = Query(5, description="최대 청크 수")
    ):
        """키워드 관련 청크만 반환"""
        doc_path = f"standards_split/KDS/{code.replace(' ', '_')}_full.json"
        if not os.path.exists(doc_path):
            raise HTTPException(404, f"Document {code} not found")
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        content = doc.get('content', '')
        relevant_chunks = []
        
        # 문단별 검색
        paragraphs = content.split('\n\n')
        for i, para in enumerate(paragraphs):
            para_lower = para.lower()
            score = sum(1 for kw in keywords if kw.lower() in para_lower)
            
            if score > 0:
                relevant_chunks.append({
                    'chunk_id': i,
                    'score': score,
                    'content': para[:1000],  # 최대 1000자
                    'tokens': processor.estimate_tokens(para[:1000]),
                    'keywords_found': [kw for kw in keywords if kw.lower() in para_lower]
                })
        
        # 점수순 정렬
        relevant_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            "code": code,
            "keywords": keywords,
            "total_found": len(relevant_chunks),
            "chunks": relevant_chunks[:max_chunks]
        }

# 사용 예시
if __name__ == "__main__":
    # 테스트
    processor = ChunkedDocumentProcessor()
    
    test_content = "매우 긴 문서 내용..." * 1000
    
    print("=== 청크 테스트 ===")
    for chunk in processor.chunk_document(test_content, chunk_tokens=500):
        print(f"Chunk {chunk['chunk_index']}: {chunk['tokens']} tokens")