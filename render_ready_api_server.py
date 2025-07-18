#!/usr/bin/env python3
"""
Render 배포 최적화 API 서버
- 경로 문제 완전 해결
- 자동 폴백 메커니즘
- 강화된 오류 처리
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import os
import logging
from datetime import datetime
import glob
import uvicorn

# 환경 변수
API_KEY = os.getenv("API_KEY", "kcsc-gpt-secure-key-2025")
PORT = int(os.getenv("PORT", 10000))

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="Korean Construction Standards API (Render Ready)",
    description="Render 배포 최적화 한국 건설표준 API",
    version="3.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 전역 데이터
search_index = {}
split_index = {}
standards_cache = {}

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str

def find_file(filename: str, search_dirs: List[str] = None) -> Optional[str]:
    """파일을 여러 경로에서 찾기"""
    if search_dirs is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs = [
            current_dir,
            ".",
            "..",
            os.path.join(current_dir, ".."),
        ]
    
    for directory in search_dirs:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            return file_path
    
    return None

def load_search_index() -> bool:
    """검색 인덱스 로드"""
    global search_index
    
    # search_index.json 찾기
    index_path = find_file("search_index.json")
    
    if index_path:
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                search_index = json.load(f)
            logger.info(f"✅ Search index loaded from {index_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load search index: {e}")
    
    # 대체: split_index에서 생성
    split_path = find_file("standards_split/split_index.json")
    if not split_path:
        split_path = find_file("split_index.json", ["./standards_split", "standards_split"])
    
    if split_path:
        try:
            with open(split_path, 'r', encoding='utf-8') as f:
                split_data = json.load(f)
            
            # search_index 형식으로 변환
            search_index = {
                "version": "3.0",
                "created": datetime.now().isoformat(),
                "total_documents": len(split_data.get('standards', {})),
                "code_index": {}
            }
            
            for code, info in split_data.get('standards', {}).items():
                search_index["code_index"][code] = {
                    "title": info.get('title', ''),
                    "category": code.split()[0] if ' ' in code else code[:3],
                    "quality_score": 85,
                    "has_full": info.get('has_full', False),
                    "has_parts": info.get('has_parts', False),
                    "size_kb": info.get('size_kb', 0)
                }
            
            logger.info(f"✅ Search index created from split_index: {len(search_index['code_index'])} entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create search index from split_index: {e}")
    
    logger.error("❌ No search index data available")
    return False

def load_split_index() -> bool:
    """분할 인덱스 로드"""
    global split_index
    
    # split_index.json 찾기
    split_path = find_file("standards_split/split_index.json")
    if not split_path:
        split_path = find_file("split_index.json", ["./standards_split", "standards_split"])
    
    if split_path:
        try:
            with open(split_path, 'r', encoding='utf-8') as f:
                split_index = json.load(f)
            logger.info(f"✅ Split index loaded from {split_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load split index: {e}")
    
    logger.error("❌ Split index not found")
    return False

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 데이터 로드"""
    logger.info("🚀 Starting Render-ready API server...")
    
    # 데이터 로드
    search_loaded = load_search_index()
    split_loaded = load_split_index()
    
    if not search_loaded and not split_loaded:
        logger.error("❌ No data loaded! Server may not function properly.")
    else:
        logger.info("✅ Server ready!")

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_loaded": {
            "search_index": len(search_index.get("code_index", {})),
            "split_index": len(split_index.get("standards", {}))
        }
    }

@app.post("/search", response_model=SearchResponse)
async def search_standards(
    request: SearchRequest,
    x_api_key: Optional[str] = Header(None)
):
    """표준 검색"""
    try:
        query = request.query.strip()
        limit = min(request.limit or 5, 20)
        
        results = []
        
        # search_index에서 검색
        if search_index.get("code_index"):
            for code, info in search_index["code_index"].items():
                if (query.lower() in code.lower() or 
                    query.lower() in info.get("title", "").lower()):
                    results.append({
                        "code": code,
                        "title": info.get("title", ""),
                        "category": info.get("category", ""),
                        "quality_score": info.get("quality_score", 0),
                        "has_full": info.get("has_full", False),
                        "has_parts": info.get("has_parts", False)
                    })
                    
                    if len(results) >= limit:
                        break
        
        # split_index에서 추가 검색 (결과가 부족한 경우)
        if len(results) < limit and split_index.get("standards"):
            for code, info in split_index["standards"].items():
                if code not in [r["code"] for r in results]:
                    if (query.lower() in code.lower() or 
                        query.lower() in info.get("title", "").lower()):
                        results.append({
                            "code": code,
                            "title": info.get("title", ""),
                            "category": code.split()[0] if ' ' in code else code[:3],
                            "quality_score": 85,
                            "has_full": info.get("has_full", False),
                            "has_parts": info.get("has_parts", False)
                        })
                        
                        if len(results) >= limit:
                            break
        
        return SearchResponse(
            results=results[:limit],
            total=len(results),
            query=query
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/standard/{code}")
async def get_standard(
    code: str,
    x_api_key: Optional[str] = Header(None)
):
    """특정 표준 조회"""
    try:
        # search_index에서 찾기
        if code in search_index.get("code_index", {}):
            return search_index["code_index"][code]
        
        # split_index에서 찾기
        if code in split_index.get("standards", {}):
            return split_index["standards"][code]
        
        raise HTTPException(status_code=404, detail=f"Standard {code} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get standard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Korean Construction Standards API",
        "version": "3.0.0",
        "status": "ready",
        "endpoints": ["/health", "/search", "/standard/{code}"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)