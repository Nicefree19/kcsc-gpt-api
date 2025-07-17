"""
경량화된 GPT API 서버 (무료 클라우드용)
- 메모리 사용 최적화
- 파일 기반 검색 (ChromaDB 없이)
- 빠른 시작 시간
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
import os
import logging
from datetime import datetime
from functools import lru_cache

# 환경 변수
API_KEY = os.getenv("API_KEY", "kcsc-gpt-secure-key-2025")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 로깅 설정
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="Korean Construction Standards API (Lite)",
    description="경량화된 한국 건설표준 API",
    version="1.0.0"
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


# Pydantic 모델
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field("keyword", description="keyword, code, category")
    limit: int = Field(10, ge=1, le=50)


class SearchResult(BaseModel):
    code: str
    title: str
    content: str
    relevance_score: float
    metadata: Optional[Dict[str, Any]] = None


# 의존성
async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# 데이터 로드 함수
@lru_cache()
def load_data():
    """JSON 파일에서 데이터 로드"""
    global documents_cache, search_index

    try:
        # 검색 인덱스 로드
        index_path = "./search_index.json"
        with open(index_path, 'r', encoding='utf-8') as f:
            search_index = json.load(f)

        # 문서 데이터 로드 (필요한 파일만)
        data_files = [
            "kcsc_structure.json",
            "kcsc_civil.json",
            "kcsc_building.json",
            "kcsc_facility.json",
            "kcsc_excs.json"
        ]

        for filename in data_files:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for doc in data.get('documents', []):
                        documents_cache[doc['id']] = doc

        logger.info(f"Loaded {len(documents_cache)} documents")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise


# 시작 시 데이터 로드
@app.on_event("startup")
async def startup_event():
    load_data()
    logger.info("API server started")


# 엔드포인트
@app.get("/")
async def root():
    return {
        "name": "Korean Construction Standards API (Lite)",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "documents_loaded": len(documents_cache)
    }


@app.post("/api/v1/search")
async def search_standards(
    request: SearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """간단한 검색 기능"""
    results = []

    if request.search_type == "code":
        # 코드 검색
        if request.query in search_index.get('code_index', {}):
            doc_id = request.query
            if doc_id in documents_cache:
                doc = documents_cache[doc_id]
                results.append(SearchResult(
                    code=doc_id,
                    title=doc.get('title', ''),
                    content=doc.get('content', {}).get('full', '')[:500] + '...',
                    relevance_score=1.0,
                    metadata=doc.get('metadata')
                ))

    elif request.search_type == "category":
        # 카테고리 검색
        category_docs = search_index.get('category_index', {}).get(
            request.query, []
        )
        for doc_id in category_docs[:request.limit]:
            if doc_id in documents_cache:
                doc = documents_cache[doc_id]
                results.append(SearchResult(
                    code=doc_id,
                    title=doc.get('title', ''),
                    content=f"카테고리: {request.query}",
                    relevance_score=0.8,
                    metadata=doc.get('metadata')
                ))

    else:  # keyword search
        # 간단한 키워드 검색 (제목과 내용에서)
        query_lower = request.query.lower()

        for doc_id, doc in documents_cache.items():
            title = doc.get('title', '').lower()
            content = doc.get('content', {}).get('full', '').lower()

            # 제목에 있으면 높은 점수
            if query_lower in title:
                results.append((1.0, doc_id, doc))
            # 내용에 있으면 중간 점수
            elif query_lower in content:
                results.append((0.5, doc_id, doc))

        # 점수순 정렬
        results.sort(key=lambda x: x[0], reverse=True)

        # 결과 포맷팅
        formatted_results = []
        for score, doc_id, doc in results[:request.limit]:
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
        raise HTTPException(
            status_code=404, detail=f"Standard {code} not found"
        )

    doc = documents_cache[code]

    return {
        "success": True,
        "data": {
            "code": code,
            "title": doc.get('title', ''),
            "full_content": doc.get('content', {}).get('full', ''),
            "sections": doc.get('content', {}).get('sections', {}),
            "metadata": doc.get('metadata', {}),
            "related_standards": doc.get('metadata', {}).get(
                'references', []
            )[:10]
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
        keywords = [
            kw for kw in keywords
            if kw.lower().startswith(prefix.lower())
        ]

    # 빈도순 정렬
    keywords.sort(
        key=lambda x: len(search_index['keyword_index'].get(x, [])),
        reverse=True
    )

    return {
        "success": True,
        "data": {"keywords": keywords[:limit], "total": len(keywords)},
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/stats")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """통계 정보"""
    return {
        "success": True,
        "data": {
            "total_documents": len(documents_cache),
            "total_categories": len(search_index.get('category_index', {})),
            "total_keywords": len(search_index.get('keyword_index', {})),
            "server_type": "lightweight",
            "memory_usage_mb": "< 512"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/openapi.json")
async def get_openapi_schema():
    """OpenAPI 스키마 제공 (GPT Actions용)"""
    return app.openapi()


# 메인
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)