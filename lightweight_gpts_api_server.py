"""
경량화된 GPT API 서버 v2 (무료 클라우드용)
- 메모리 사용 최적화
- 파일 기반 검색 (ChromaDB 없이)
- 빠른 시작 시간
- 청크 기반 응답 지원 (v2 features)
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import os
import logging
from datetime import datetime
from functools import lru_cache
import hashlib
import re

# 환경 변수
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SPLIT_DATA_PATH = os.getenv("SPLIT_DATA_PATH", "./gpts_data/standards_split")

# 로깅 설정
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="Korean Construction Standards API",
    description="경량화된 한국 건설표준 API (v1 + v2 통합)",
    version="2.0.0",
    servers=[
        {"url": "https://kcsc-gpt-api.onrender.com", "description": "Production Server"},
        {"url": "http://localhost:8000", "description": "Local Development Server"}
    ]
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.openai.com", "https://chatgpt.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 전역 변수
documents_cache = {}
search_index = {}
split_index = {}

# Pydantic 모델
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field("keyword", description="keyword, code, category")
    limit: int = Field(10, ge=1, le=50)

class SearchResult(BaseModel):
    code: str
    title: str
    content: str  # v1 호환성을 위해 유지
    preview: Optional[str] = None  # v2 feature
    relevance_score: float
    metadata: Optional[Dict[str, Any]] = None
    available: Optional[Dict[str, Any]] = None  # v2 feature: 사용 가능한 섹션/파트 정보

# v2 추가 모델
class StandardSummary(BaseModel):
    code: str
    title: str
    metadata: Dict[str, Any]
    preview: str
    available_sections: List[str]
    statistics: Dict[str, Any]

class StandardSection(BaseModel):
    code: str
    title: str
    section: str
    content: str

class StandardPart(BaseModel):
    code: str
    title: str
    part: int
    total_parts: int
    content: str

# 의존성

def normalize_code(code_str):
    """코드를 표준 형식으로 정규화"""
    if not code_str:
        return code_str
        
    # 언더스코어나 하이픈을 공백으로 변경
    normalized = code_str.replace('_', ' ').replace('-', ' ')
    
    # 연속된 공백을 하나로
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # 표준 형식 확인 (예: KDS 14 20 01)
    match = re.match(r'(KDS|KCS|EXCS|SMCS|LHCS)\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})', normalized)
    if match:
        prefix = match.group(1)
        level1 = match.group(2).zfill(2)
        level2 = match.group(3).zfill(2)
        level3 = match.group(4).zfill(2)
        return f"{prefix} {level1} {level2} {level3}"
        
    return normalized


async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# 데이터 로드 함수
@lru_cache()
def load_data():
    """JSON 파일에서 데이터 로드 (v1 + v2 통합)"""
    global documents_cache, search_index, split_index
    
    try:
        # 1. 검색 인덱스 로드
        index_path = os.getenv("INDEX_PATH", "./gpts_data/search_index.json")
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                search_index = json.load(f)
            logger.info("Loaded search index")
        
        # 2. 분할 인덱스 로드 (v2)
        split_index_path = os.path.join(SPLIT_DATA_PATH, "split_index.json")
        if os.path.exists(split_index_path):
            with open(split_index_path, 'r', encoding='utf-8') as f:
                split_index = json.load(f)
            logger.info(f"Loaded split index with {len(split_index.get('standards', {}))} standards")
        
        # 3. 문서 데이터 로드 (v1 호환성)
        data_files = [
            "kcsc_structure.json",
            "kcsc_civil.json", 
            "kcsc_building.json",
            "kcsc_facility.json",
            "kcsc_excs.json"
        ]
        
        for filename in data_files:
            filepath = f"./gpts_data/{filename}"
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for doc in data.get('documents', []):
                        documents_cache[doc['id']] = doc
        
        logger.info(f"Loaded {len(documents_cache)} full documents, {len(split_index.get('standards', {}))} split standards")
        
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise

# 시작 시 데이터 로드
@app.on_event("startup")
async def startup_event():
    load_data()
    logger.info("API server v2 started (with v1 compatibility)")

# 엔드포인트
@app.get("/")
async def root():
    return {
        "name": "Korean Construction Standards API",
        "version": "2.0.0",
        "status": "operational",
        "features": ["v1_compatibility", "chunked_responses", "section_loading", "summary_preview"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "documents_loaded": len(documents_cache),
        "standards_split": len(split_index.get('standards', {}))
    }

@app.post("/api/v1/search")
async def search_standards(
    request: SearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """검색 기능 (v1 + v2 통합)"""
    results = []
    
    if request.search_type == "code":
        # 코드 검색 - v2 우선, v1 폴백
        if request.query in split_index.get('standards', {}):
            # v2: 분할된 표준에서 검색
            std_info = split_index['standards'][request.query]
            summary = await _load_summary(request.query)
            if summary:
                results.append(SearchResult(
                    code=request.query,
                    title=std_info['title'],
                    content=summary.get('preview', '')[:500] + '...',  # v1 호환성
                    preview=summary.get('preview', '')[:500],  # v2 feature
                    relevance_score=1.0,
                    metadata=summary.get('metadata', {}),
                    available={
                        'has_full': std_info.get('has_full', False),
                        'has_parts': std_info.get('has_parts', False),
                        'sections': summary.get('available_sections', []),
                        'size_kb': std_info.get('size_kb', 0)
                    }
                ))
        elif request.query in documents_cache:
            # v1: 기존 캐시에서 검색
            doc = documents_cache[request.query]
            results.append(SearchResult(
                code=request.query,
                title=doc.get('title', ''),
                content=doc.get('content', {}).get('full', '')[:500] + '...',
                relevance_score=1.0,
                metadata=doc.get('metadata')
            ))
    
    elif request.search_type == "category":
        # 카테고리 검색
        category_docs = search_index.get('category_index', {}).get(request.query, [])
        for doc_id in category_docs[:request.limit]:
            # v2 우선 확인
            if doc_id in split_index.get('standards', {}):
                std_info = split_index['standards'][doc_id]
                summary = await _load_summary(doc_id)
                if summary:
                    results.append(SearchResult(
                        code=doc_id,
                        title=std_info['title'],
                        content=f"카테고리: {request.query}",
                        preview=summary.get('preview', '')[:200],
                        relevance_score=0.8,
                        metadata=summary.get('metadata', {}),
                        available={
                            'has_full': std_info.get('has_full', False),
                            'has_parts': std_info.get('has_parts', False),
                            'sections': summary.get('available_sections', [])
                        }
                    ))
            elif doc_id in documents_cache:
                # v1 폴백
                doc = documents_cache[doc_id]
                results.append(SearchResult(
                    code=doc_id,
                    title=doc.get('title', ''),
                    content=f"카테고리: {request.query}",
                    relevance_score=0.8,
                    metadata=doc.get('metadata')
                ))
    
    else:  # keyword search
        query_lower = normalize_code(request.query).lower()
        
        # v2 표준에서 검색
        for code, std_info in split_index.get('standards', {}).items():
            if query_lower in std_info['title'].lower():
                summary = await _load_summary(code)
                if summary:
                    results.append((0.7, code, std_info, summary))
                    
        # v1 문서에서 검색
        for doc_id, doc in documents_cache.items():
            if doc_id not in split_index.get('standards', {}):  # 중복 방지
                title = doc.get('title', '').lower()
                content = doc.get('content', {}).get('full', '').lower()
                
                if query_lower in title:
                    results.append((1.0, doc_id, doc, None))
                elif query_lower in content:
                    results.append((0.5, doc_id, doc, None))
        
        # 정렬 및 포맷팅
        results.sort(key=lambda x: x[0], reverse=True)
        formatted_results = []
        
        for item in results[:request.limit]:
            if len(item) == 4:  # v2 결과
                score, code, std_info, summary = item
                formatted_results.append(SearchResult(
                    code=code,
                    title=std_info['title'],
                    content=summary.get('preview', '')[:500] + '...' if summary else '',
                    preview=summary.get('preview', '')[:500] if summary else '',
                    relevance_score=score,
                    metadata=summary.get('metadata', {}) if summary else {},
                    available={
                        'has_full': std_info.get('has_full', False),
                        'has_parts': std_info.get('has_parts', False),
                        'sections': summary.get('available_sections', []) if summary else []
                    }
                ))
            else:  # v1 결과
                score, doc_id, doc = item[:3]
                formatted_results.append(SearchResult(
                    code=doc_id,
                    title=doc.get('title', ''),
                    content=doc.get('content', {}).get('full', '')[:500] + '...',
                    relevance_score=score,
                    metadata=doc.get('metadata')
                ))
        
        results = formatted_results
    
    return {
        "success": True,
        "data": {"results": results, "total": len(results)},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/standard/{code}")
async def get_standard_detail(
    code: str,
    api_key: str = Depends(verify_api_key)
):
    """표준 상세 조회"""
    if code not in documents_cache:
        raise HTTPException(status_code=404, detail=f"Standard {code} not found")
    
    doc = documents_cache[code]
    
    return {
        "success": True,
        "data": {
            "code": code,
            "title": doc.get('title', ''),
            "full_content": doc.get('content', {}).get('full', ''),
            "sections": doc.get('content', {}).get('sections', {}),
            "metadata": doc.get('metadata', {}),
            "related_standards": doc.get('metadata', {}).get('references', [])[:10]
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/keywords")
async def get_keywords(
    prefix: Optional[str] = None,
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """키워드 목록"""
    keywords = list(search_index.get('keyword_index', {}).keys())
    
    if prefix:
        keywords = [kw for kw in keywords if kw.lower().startswith(prefix.lower())]
    
    # 빈도순 정렬
    keywords.sort(key=lambda x: len(search_index['keyword_index'].get(x, [])), reverse=True)
    
    return {
        "success": True,
        "data": {"keywords": keywords[:limit], "total": len(keywords)},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/stats")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """통계 정보"""
    stats = split_index.get('statistics', {})
    return {
        "success": True,
        "data": {
            "total_documents": len(documents_cache),
            "total_standards_split": len(split_index.get('standards', {})),
            "total_categories": len(search_index.get('category_index', {})),
            "total_keywords": len(search_index.get('keyword_index', {})),
            "total_size_mb": stats.get('total_size_mb', 0),
            "large_documents": len(stats.get('large_documents', [])),
            "server_type": "lightweight_v2",
            "api_version": "2.0",
            "features": ["v1_compatibility", "chunked_loading", "section_access", "summary_preview"],
            "memory_usage_mb": "< 512"
        },
        "timestamp": datetime.now().isoformat()
    }

# v2 추가 엔드포인트: 요약
@app.get("/api/v1/standard/{code}/summary")
async def get_standard_summary(
    code: str,
    api_key: str = Depends(verify_api_key)
):
    """표준 요약 정보 (v2)"""
    summary = await _load_summary(code)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Standard {code} not found")
    
    return {
        "success": True,
        "data": summary,
        "timestamp": datetime.now().isoformat()
    }

# v2 추가 엔드포인트: 섹션
@app.get("/api/v1/standard/{code}/section/{section}")
async def get_standard_section(
    code: str,
    section: str,
    api_key: str = Depends(verify_api_key)
):
    """특정 섹션 내용 (v2)"""
    safe_code = code.replace(' ', '_').replace('/', '_')
    category = code.split()[0] if ' ' in code else code[:3]
    
    section_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_section_{section}.json")
    
    if not os.path.exists(section_path):
        raise HTTPException(status_code=404, detail=f"Section {section} not found")
    
    try:
        with open(section_path, 'r', encoding='utf-8') as f:
            section_data = json.load(f)
        
        return {
            "success": True,
            "data": StandardSection(**section_data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error loading section: {e}")
        raise HTTPException(status_code=500, detail="Error loading section")

# v2 추가 엔드포인트: 파트
@app.get("/api/v1/standard/{code}/part/{part}")
async def get_standard_part(
    code: str,
    part: int,
    api_key: str = Depends(verify_api_key)
):
    """특정 파트 내용 (v2)"""
    safe_code = code.replace(' ', '_').replace('/', '_')
    category = code.split()[0] if ' ' in code else code[:3]
    
    part_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_part{part}.json")
    
    if not os.path.exists(part_path):
        raise HTTPException(status_code=404, detail=f"Part {part} not found")
    
    try:
        with open(part_path, 'r', encoding='utf-8') as f:
            part_data = json.load(f)
        
        return {
            "success": True,
            "data": StandardPart(**part_data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error loading part: {e}")
        raise HTTPException(status_code=500, detail="Error loading part")

# v2 추가 엔드포인트: 정보
@app.get("/api/v1/standard/{code}/info")
async def get_standard_info(
    code: str,
    api_key: str = Depends(verify_api_key)
):
    """표준 구조 정보 (v2)"""
    safe_code = code.replace(' ', '_').replace('/', '_')
    category = code.split()[0] if ' ' in code else code[:3]
    
    info_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_info.json")
    
    if os.path.exists(info_path):
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                info_data = json.load(f)
            
            return {
                "success": True,
                "data": info_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error loading info: {e}")
    
    # info 파일이 없으면 기본 정보 반환
    if code in split_index.get('standards', {}):
        std_info = split_index['standards'][code]
        return {
            "success": True,
            "data": {
                "code": code,
                "title": std_info['title'],
                "has_full": std_info.get('has_full', False),
                "has_parts": std_info.get('has_parts', False),
                "size_kb": std_info.get('size_kb', 0)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    raise HTTPException(status_code=404, detail=f"Standard {code} not found")

# 헬퍼 함수
async def _load_summary(code: str) -> Optional[Dict]:
    """요약 파일 로드"""
    safe_code = code.replace(' ', '_').replace('/', '_')
    category = code.split()[0] if ' ' in code else code[:3]
    
    summary_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_summary.json")
    
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading summary for {code}: {e}")
    
    return None

# OpenAPI 스키마 커스터마이징
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 서버 정보 추가
    openapi_schema["servers"] = [
        {"url": "https://kcsc-gpt-api.onrender.com", "description": "Production Server"}
    ]
    
    # API Key 보안 스키마 추가
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    # 전역 보안 설정
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# OpenAPI 스키마 설정
app.openapi = custom_openapi

# 메인
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)