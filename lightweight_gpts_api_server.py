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
# 현재 파일 기준 상대 경로로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_DATA_PATH = os.getenv("SPLIT_DATA_PATH", os.path.join(SCRIPT_DIR, "standards_split"))
GPT_ACTIONS_MODE = os.getenv("GPT_ACTIONS_MODE", "false").lower() == "true"  # GPT Actions 모드

# 로깅 설정
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# FastAPI 2.0+ 방식으로 변경
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    load_data()
    logger.info(f"API server v2 started (GPT Actions Mode: {GPT_ACTIONS_MODE})")
    yield
    # 종료 시 실행 (필요 시)

# FastAPI 앱
app = FastAPI(
    title="Korean Construction Standards API",
    description="경량화된 한국 건설표준 API (v1 + v2 통합)",
    version="2.0.0",
    servers=[
        {"url": "https://kcsc-gpt-api.onrender.com", "description": "Production Server"},
        {"url": "http://localhost:8000", "description": "Local Development Server"}
    ],
    lifespan=lifespan
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
    """코드를 표준 형식으로 정규화 - 다양한 입력 형식 지원"""
    if not code_str:
        return code_str
    
    # 1. 대문자로 변환
    normalized = code_str.upper().strip()
    
    # 2. 특수문자를 공백으로 변경
    normalized = normalized.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    
    # 3. 연속된 공백을 하나로
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # 4. 표준 형식 확인 (예: KDS 14 20 01)
    match = re.match(r'(KDS|KCS|EXCS|SMCS|LHCS)\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})', normalized)
    if match:
        prefix = match.group(1)
        level1 = match.group(2).zfill(2)
        level2 = match.group(3).zfill(2)
        level3 = match.group(4).zfill(2)
        return f"{prefix} {level1} {level2} {level3}"
    
    # 5. 붙어있는 형식 처리 (예: KDS142001)
    for prefix in ['KDS', 'KCS', 'EXCS', 'SMCS', 'LHCS']:
        if normalized.startswith(prefix):
            # 접두사 뒤의 숫자 추출
            nums = normalized[len(prefix):].replace(' ', '')
            if len(nums) == 6 and nums.isdigit():
                return f"{prefix} {nums[0:2]} {nums[2:4]} {nums[4:6]}"
            elif len(nums) >= 6:
                # 숫자만 추출
                digits = ''.join(c for c in nums if c.isdigit())
                if len(digits) >= 6:
                    return f"{prefix} {digits[0:2]} {digits[2:4]} {digits[4:6]}"
    
    # 6. 원본 반환 (정규화 실패 시)
    return normalized


async def verify_api_key(x_api_key: str = Header(None)):
    """API 키 검증 - GPT Actions 모드에서는 선택적"""
    if GPT_ACTIONS_MODE:
        # GPT Actions 모드에서는 API 키 검증을 스킵하거나 완화
        logger.info(f"GPT Actions request with key: {x_api_key[:10]}..." if x_api_key else "No API key")
        return x_api_key or "gpt-actions"
    else:
        # 일반 모드에서는 엄격한 검증
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return x_api_key

# 데이터 로드 함수
@lru_cache()
def load_data():
    """향상된 데이터 로딩 with 자동 폴백"""
    global documents_cache, search_index, split_index
    
    try:
        # 1. 검색 인덱스 로드 (필수)
        # 현재 스크립트 디렉토리 기준으로 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.getenv("INDEX_PATH", os.path.join(current_dir, "search_index.json"))
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                search_index = json.load(f)
            logger.info(f"✅ Search index loaded: {len(search_index.get('codes', []))} codes")
        else:
            logger.warning(f"⚠️ Search index not found at {index_path}")
        
        # 2. 분할 인덱스 로드 (v2)
        # 이미 절대 경로로 설정되어 있음
        split_index_path = os.path.join(SPLIT_DATA_PATH, "split_index.json")
        if os.path.exists(split_index_path):
            with open(split_index_path, 'r', encoding='utf-8') as f:
                split_index = json.load(f)
            logger.info(f"✅ Split index loaded: {len(split_index.get('standards', {}))} standards")
            
            # 🔥 핵심 수정: split_index 기반으로 documents_cache 생성
            for code, info in split_index.get('standards', {}).items():
                normalized_code = normalize_code(code)
                documents_cache[normalized_code] = {
                    'id': normalized_code,
                    'title': info.get('title', ''),
                    'category': code.split()[0] if ' ' in code else code[:3],
                    'content': {'full': f"[Split data] {info.get('title', '')}"},
                    'metadata': {
                        'has_parts': info.get('has_parts', False),
                        'has_full': info.get('has_full', False),
                        'sections': info.get('sections', []),
                        'source': 'split_index'
                    }
                }
        else:
            logger.warning(f"⚠️ Split index not found at {split_index_path}")
        
        # 3. 문서 데이터 로드 시도 (v1 호환성 - 있으면 좋고 없어도 됨)
        data_files = [
            "kcsc_structure.json",
            "kcsc_civil.json", 
            "kcsc_building.json",
            "kcsc_facility.json",
            "kcsc_excs.json"
        ]
        
        v1_loaded = 0
        for filename in data_files:
            filepath = os.path.join(current_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for doc in data.get('documents', []):
                            normalized_id = normalize_code(doc.get('id', ''))
                            documents_cache[normalized_id] = doc
                            v1_loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load {filename}: {e}")
        
        # 4. 🆘 긴급 폴백: 데이터가 없으면 search_index에서 생성
        if len(documents_cache) == 0 and search_index and 'codes' in search_index:
            logger.warning("🆘 No documents loaded, creating from search_index...")
            for code_info in search_index['codes']:
                code = normalize_code(code_info.get('code', ''))
                documents_cache[code] = {
                    'id': code,
                    'title': code_info.get('title', code),
                    'category': code.split()[0] if ' ' in code else code[:3],
                    'content': {'full': code_info.get('title', '')},
                    'metadata': {'source': 'search_index_fallback'}
                }
            logger.info(f"🆘 Created {len(documents_cache)} fallback entries")
        
        # 최종 로깅
        logger.info(f"""
        📊 Data Loading Summary:
        - Documents loaded: {len(documents_cache)}
        - Split standards: {len(split_index.get('standards', {}))}
        - V1 documents: {v1_loaded}
        - Status: {'✅ OK' if len(documents_cache) > 0 else '❌ CRITICAL'}
        """)
        
    except Exception as e:
        logger.error(f"💥 Critical error in load_data: {e}")
        import traceback
        logger.error(traceback.format_exc())

# 엔드포인트 시작

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
    """향상된 헬스체크 with 상세 진단"""
    status = "healthy"
    issues = []
    
    # 문서 로딩 상태 체크
    if len(documents_cache) == 0:
        status = "critical"
        issues.append("No documents loaded in cache")
    elif len(documents_cache) < 100:
        status = "degraded"
        issues.append(f"Only {len(documents_cache)} documents loaded (expected more)")
    
    # 인덱스 상태 체크
    if len(split_index.get('standards', {})) == 0:
        issues.append("No split standards loaded")
    
    if len(search_index.get('codes', [])) == 0:
        issues.append("No search index codes")
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "documents_loaded": len(documents_cache),
        "standards_split": len(split_index.get('standards', {})),
        "search_index_codes": len(search_index.get('codes', [])),
        "issues": issues,
        "mode": "GPT_ACTIONS" if GPT_ACTIONS_MODE else "STANDARD",
        "data_sources": {
            "v1_files": any(doc.get('metadata', {}).get('source') != 'split_index' 
                          for doc in documents_cache.values()),
            "split_index": any(doc.get('metadata', {}).get('source') == 'split_index' 
                              for doc in documents_cache.values()),
            "fallback": any(doc.get('metadata', {}).get('source') == 'search_index_fallback' 
                           for doc in documents_cache.values())
        }
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
    # 코드 정규화 적용
    normalized_code = normalize_code(code)
    
    if normalized_code not in documents_cache:
        raise HTTPException(status_code=404, detail=f"Standard {normalized_code} not found")
    
    doc = documents_cache[normalized_code]
    
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
    # 코드 정규화 적용
    normalized_code = normalize_code(code)
    
    summary = await _load_summary(normalized_code)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Standard {normalized_code} not found")
    
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

# ===== 경량화 엔드포인트 추가 =====

def estimate_tokens(text: str) -> int:
    """간단한 토큰 추정 (한글 2토큰, 영문 1토큰 기준)"""
    if not text:
        return 0
    korean_chars = len(re.findall(r'[가-힣]', text))
    other_chars = len(text) - korean_chars
    return korean_chars * 2 + other_chars

def create_micro_summary(doc: Dict) -> Dict:
    """초경량 요약 생성 (50토큰 이하)"""
    return {
        "code": doc.get('id', ''),
        "title": doc.get('title', '')[:50],
        "tokens": 50,
        "level": "micro"
    }

def create_mini_summary(doc: Dict, max_chars: int = 200) -> Dict:
    """미니 요약 생성 (200토큰)"""
    content = doc.get('content', {})
    if isinstance(content, dict):
        text = content.get('full', '')[:max_chars]
    else:
        text = str(content)[:max_chars]
    
    tokens = estimate_tokens(text)
    
    return {
        "code": doc.get('id', ''),
        "title": doc.get('title', ''),
        "summary": text + ("..." if len(str(content)) > max_chars else ""),
        "tokens": tokens,
        "level": "mini"
    }

def extract_key_sections(doc: Dict, keywords: List[str], max_tokens: int = 1000) -> List[Dict]:
    """키워드 관련 핵심 섹션 추출"""
    sections = []
    current_tokens = 0
    
    content = doc.get('content', {})
    if isinstance(content, str):
        # 간단한 섹션 분할 (문단 기준)
        paragraphs = content.split('\n\n')
        for i, para in enumerate(paragraphs):
            # 키워드 포함 여부 확인
            para_lower = para.lower()
            if any(kw.lower() in para_lower for kw in keywords):
                para_tokens = estimate_tokens(para)
                if current_tokens + para_tokens <= max_tokens:
                    sections.append({
                        "section_id": f"para_{i}",
                        "content": para[:500],
                        "tokens": para_tokens
                    })
                    current_tokens += para_tokens
                else:
                    break
    
    return sections

@app.get("/api/v2/lightweight/{code}")
async def get_lightweight_response(
    code: str,
    max_tokens: int = Query(2000, description="Maximum tokens in response"),
    level: str = Query("smart", description="Response level: micro, mini, smart"),
    api_key: str = Depends(verify_api_key)
):
    """경량화된 응답 - GPT 토큰 제한 고려"""
    normalized_code = normalize_code(code)
    
    # 기본 응답 구조
    response = {
        "success": True,
        "code": normalized_code,
        "max_tokens": max_tokens,
        "tokens_used": 0
    }
    
    # 문서 찾기 (캐시 우선, split_index 폴백)
    doc = None
    if normalized_code in documents_cache:
        doc = documents_cache[normalized_code]
    elif normalized_code in split_index.get('standards', {}):
        # split_index에서 기본 정보 생성
        std_info = split_index['standards'][normalized_code]
        doc = {
            'id': normalized_code,
            'title': std_info.get('title', ''),
            'content': {'full': f"[Split data available] {std_info.get('title', '')}"},
            'metadata': std_info
        }
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Standard {normalized_code} not found")
    
    # 레벨별 응답 생성
    if level == "micro":
        response["data"] = create_micro_summary(doc)
        response["tokens_used"] = 50
    
    elif level == "mini":
        response["data"] = create_mini_summary(doc)
        response["tokens_used"] = response["data"]["tokens"]
    
    else:  # smart (기본값)
        # 단계별 컨텐츠 구성
        contents = []
        
        # 1. 기본 요약 (필수)
        mini = create_mini_summary(doc, max_chars=150)
        contents.append(mini)
        response["tokens_used"] += mini["tokens"]
        
        # 2. 메타데이터 정보 (여유 있으면)
        if response["tokens_used"] < max_tokens - 100:
            metadata = doc.get('metadata', {})
            meta_info = {
                "type": "metadata",
                "category": metadata.get('category', ''),
                "sections": metadata.get('sections', [])[:5],  # 최대 5개
                "tokens": 100
            }
            contents.append(meta_info)
            response["tokens_used"] += 100
        
        # 3. split 데이터 가용성 정보
        if normalized_code in split_index.get('standards', {}):
            std_info = split_index['standards'][normalized_code]
            availability = {
                "type": "availability",
                "has_parts": std_info.get('has_parts', False),
                "has_sections": bool(std_info.get('sections', [])),
                "total_size_kb": std_info.get('size_kb', 0),
                "tokens": 50
            }
            contents.append(availability)
            response["tokens_used"] += 50
        
        response["data"] = {
            "level": "smart",
            "contents": contents,
            "suggestions": {
                "next_actions": [],
                "available_depth": "full" if response["tokens_used"] < max_tokens * 0.5 else "limited"
            }
        }
        
        # 다음 액션 제안
        if response["tokens_used"] < max_tokens * 0.3:
            response["data"]["suggestions"]["next_actions"].append("더 상세한 정보 요청 가능")
        if normalized_code in split_index.get('standards', {}):
            response["data"]["suggestions"]["next_actions"].append("섹션별 상세 내용 조회 가능")
    
    response["data"]["navigation"] = {
        "endpoints": {
            "summary": f"/api/v1/standard/{normalized_code}/summary",
            "sections": f"/api/v1/standard/{normalized_code}/section/{{section}}",
            "parts": f"/api/v1/standard/{normalized_code}/part/{{part}}"
        }
    }
    
    return response

@app.post("/api/v2/smart-search")
async def smart_search(
    query: str = Query(..., description="Search query"),
    intent: Optional[str] = Query(None, description="Query intent: definition, calculation, requirement"),
    max_results: int = Query(5, description="Maximum results"),
    max_tokens_per_result: int = Query(500, description="Max tokens per result"),
    api_key: str = Depends(verify_api_key)
):
    """스마트 검색 - 의도 기반 경량 응답"""
    
    # 의도 분석
    detected_intent = intent
    if not detected_intent:
        # 간단한 의도 추측
        query_lower = query.lower()
        if any(word in query_lower for word in ['뭐야', '무엇', '정의', 'what']):
            detected_intent = 'definition'
        elif any(word in query_lower for word in ['계산', '공식', 'formula']):
            detected_intent = 'calculation'
        elif any(word in query_lower for word in ['기준', '규정', 'requirement']):
            detected_intent = 'requirement'
        else:
            detected_intent = 'general'
    
    # 일반 검색 수행
    results = []
    query_normalized = normalize_code(query)
    
    # 코드 직접 매칭 시도
    if query_normalized in documents_cache:
        doc = documents_cache[query_normalized]
        result = create_mini_summary(doc, max_chars=max_tokens_per_result // 4)
        result['relevance'] = 1.0
        result['match_type'] = 'exact_code'
        results.append(result)
    
    # 키워드 검색
    if len(results) < max_results:
        query_lower = query.lower()
        for code, doc in documents_cache.items():
            if len(results) >= max_results:
                break
                
            title = doc.get('title', '').lower()
            if query_lower in title or query_lower in code.lower():
                result = create_mini_summary(doc, max_chars=max_tokens_per_result // 4)
                result['relevance'] = 0.7 if query_lower in title else 0.5
                result['match_type'] = 'keyword'
                results.append(result)
    
    # 결과 정렬
    results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
    
    return {
        "success": True,
        "query": query,
        "intent": detected_intent,
        "results": results[:max_results],
        "total_results": len(results),
        "suggestions": {
            "refine_query": detected_intent == 'general',
            "use_code_search": len(results) == 0
        }
    }

# OpenAPI 스키마 설정
app.openapi = custom_openapi

# 메인
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)