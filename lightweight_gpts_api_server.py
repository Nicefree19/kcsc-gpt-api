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
from typing import Iterator
from fastapi.responses import StreamingResponse

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
section_indexes = {}  # 섹션 인덱스 캐시
topic_cache = {}  # 주제별 요약 캐시

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

# 청크 응답 모델
class ChunkedResponse(BaseModel):
    code: str
    query: Optional[str] = None
    total_chunks: int
    current_chunk: int
    chunks: List[Dict[str, Any]]
    next_chunk: Optional[int] = None
    completed: bool

# 섹션 인덱스 모델
class SectionIndex(BaseModel):
    code: str
    title: str
    total_length: int
    sections: List[Dict[str, Any]]
    formulas: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    quick_access: Dict[str, Any]

# 주제별 요약 모델
class TopicSummary(BaseModel):
    code: str
    topic: str
    title: str
    summary: str
    key_points: List[str]
    formulas: List[str]
    tables: List[str]
    generated_at: str
    tokens: int

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

# === 대용량 문서 처리를 위한 새로운 엔드포인트 ===

# 청크 처리 클래스
class ChunkedDocumentProcessor:
    """대용량 문서를 청크로 분할하여 처리"""
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        
    def estimate_tokens(self, text: str) -> int:
        """간단한 토큰 추정"""
        korean_chars = len([c for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3])
        other_chars = len(text) - korean_chars
        return korean_chars * 2 + other_chars
    
    def chunk_document(self, content: str, chunk_tokens: int = 1000) -> Iterator[Dict[str, Any]]:
        """문서를 토큰 크기별로 청크 분할"""
        paragraphs = content.split('\n\n')
        
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)
            
            if current_tokens + para_tokens <= chunk_tokens:
                current_chunk.append(para)
                current_tokens += para_tokens
            else:
                if current_chunk:
                    yield {
                        'chunk_index': chunk_index,
                        'content': '\n\n'.join(current_chunk),
                        'tokens': current_tokens,
                        'has_more': True
                    }
                    chunk_index += 1
                
                current_chunk = [para]
                current_tokens = para_tokens
        
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
            yield from self.chunk_document(content)
    
    def _find_relevant_sections(self, content: str, query: str) -> list:
        """쿼리 관련 섹션 찾기"""
        sections = []
        query_lower = query.lower()
        
        parts = content.split('\n# ')
        
        for part in parts:
            if any(keyword in part.lower() for keyword in query_lower.split()):
                sections.append({
                    'content': part[:2000],
                    'tokens': self.estimate_tokens(part[:2000]),
                    'title': part.split('\n')[0][:50]
                })
        
        return sections[:5]

# 청크 프로세서 인스턴스
chunk_processor = ChunkedDocumentProcessor()

# 1. 청크 기반 문서 반환
@app.get("/api/v2/standard/{code}/chunked")
async def get_chunked_document(
    code: str,
    chunk_size: int = Query(1000, description="청크당 최대 토큰"),
    query: Optional[str] = Query(None, description="검색 쿼리"),
    start_chunk: int = Query(0, description="시작 청크 인덱스"),
    api_key: str = Depends(verify_api_key)
):
    """대용량 문서를 청크 단위로 반환"""
    normalized = normalize_code(code)
    
    # 전체 문서 로드 시도
    safe_code = normalized.replace(' ', '_')
    category = normalized.split()[0] if ' ' in normalized else normalized[:3]
    full_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_full.json")
    
    if not os.path.exists(full_path):
        # 요약본으로 폴백
        summary_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            doc['content'] = doc.get('preview', '')
        else:
            raise HTTPException(404, f"Document {code} not found")
    else:
        with open(full_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
    
    # 청크 생성
    chunks = list(chunk_processor.create_smart_chunks(doc, query))
    
    # 페이지네이션
    if start_chunk >= len(chunks):
        return ChunkedResponse(
            code=normalized,
            query=query,
            total_chunks=len(chunks),
            current_chunk=start_chunk,
            chunks=[],
            completed=True
        )
    
    page_chunks = chunks[start_chunk:start_chunk + 3]
    
    return ChunkedResponse(
        code=normalized,
        query=query,
        total_chunks=len(chunks),
        current_chunk=start_chunk,
        chunks=page_chunks,
        next_chunk=start_chunk + len(page_chunks) if start_chunk + len(page_chunks) < len(chunks) else None,
        completed=start_chunk + len(page_chunks) >= len(chunks)
    )

# 2. 섹션 인덱스 반환
@app.get("/api/v2/standard/{code}/section-index")
async def get_section_index(
    code: str,
    api_key: str = Depends(verify_api_key)
):
    """문서의 섹션 인덱스 반환"""
    normalized = normalize_code(code)
    
    # 캐시 확인
    if normalized in section_indexes:
        return section_indexes[normalized]
    
    # 섹션 인덱스 생성
    safe_code = normalized.replace(' ', '_')
    category = normalized.split()[0] if ' ' in normalized else normalized[:3]
    full_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_full.json")
    
    if not os.path.exists(full_path):
        raise HTTPException(404, f"Document {code} not found")
    
    with open(full_path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    
    content = doc.get('content', '')
    sections = _extract_sections(content)
    formulas = _extract_formulas(content)
    tables = _extract_tables(content)
    
    index = SectionIndex(
        code=normalized,
        title=doc.get('title', ''),
        total_length=len(content),
        sections=sections,
        formulas=formulas,
        tables=tables,
        quick_access={
            'key_sections': [s for s in sections if any(
                keyword in s['title'].lower() 
                for keyword in ['정착', '이음', '길이', '계산', '요구사항']
            )][:5],
            'has_formulas': len(formulas) > 0,
            'formula_count': len(formulas),
            'has_tables': len(tables) > 0,
            'table_count': len(tables)
        }
    )
    
    # 캐시 저장
    section_indexes[normalized] = index
    
    return index

# 3. 주제별 요약 반환
@app.get("/api/v2/standard/{code}/topic/{topic}")
async def get_topic_summary(
    code: str,
    topic: str,
    api_key: str = Depends(verify_api_key)
):
    """주제별 요약 반환"""
    normalized = normalize_code(code)
    cache_key = f"{normalized}:{topic}"
    
    # 캐시 확인
    if cache_key in topic_cache:
        return topic_cache[cache_key]
    
    # 사전 정의된 주제
    common_topics = {
        '정착길이': {
            'keywords': ['정착', '정착길이', '묻힘길이', 'anchorage'],
            'sections': ['정착 및 이음', '철근의 정착', '인장철근']
        },
        '이음길이': {
            'keywords': ['이음', '이음길이', '겹침이음', 'splice'],
            'sections': ['이음', '철근의 이음', '겹침이음']
        },
        '피복두께': {
            'keywords': ['피복', '피복두께', '최소피복두께'],
            'sections': ['피복두께', '콘크리트 피복']
        },
        '전단': {
            'keywords': ['전단', '전단력', '전단철근'],
            'sections': ['전단설계', '전단보강']
        },
        '균열': {
            'keywords': ['균열', '균열폭', '균열제어'],
            'sections': ['균열제어', '사용성']
        }
    }
    
    if topic not in common_topics:
        return {
            "error": "Topic not found",
            "available_topics": list(common_topics.keys())
        }
    
    # 문서 로드
    safe_code = normalized.replace(' ', '_')
    category = normalized.split()[0] if ' ' in normalized else normalized[:3]
    full_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_full.json")
    
    if not os.path.exists(full_path):
        # 요약본으로 시도
        summary_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            content = doc.get('preview', '')
        else:
            raise HTTPException(404, f"Document {code} not found")
    else:
        with open(full_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        content = doc.get('content', '')
    
    # 관련 내용 추출
    topic_config = common_topics[topic]
    relevant_content = _extract_relevant_content(
        content, 
        topic_config['keywords'],
        topic_config.get('sections', [])
    )
    
    # 요약 생성
    summary = TopicSummary(
        code=normalized,
        topic=topic,
        title=f"{doc.get('title', '')} - {topic}",
        summary=_create_topic_summary(topic, relevant_content),
        key_points=_extract_key_points(relevant_content),
        formulas=_extract_topic_formulas(relevant_content),
        tables=_extract_topic_tables(relevant_content),
        generated_at=datetime.now().isoformat(),
        tokens=len(relevant_content) // 3
    )
    
    # 캐시 저장
    topic_cache[cache_key] = summary
    
    return summary

# 4. 스트리밍 응답
@app.get("/api/v2/standard/{code}/stream")
async def stream_document(
    code: str,
    chunk_tokens: int = Query(500, description="청크당 토큰"),
    api_key: str = Depends(verify_api_key)
):
    """문서를 스트리밍으로 반환"""
    normalized = normalize_code(code)
    
    safe_code = normalized.replace(' ', '_')
    category = normalized.split()[0] if ' ' in normalized else normalized[:3]
    full_path = os.path.join(SPLIT_DATA_PATH, category, f"{safe_code}_full.json")
    
    if not os.path.exists(full_path):
        raise HTTPException(404, f"Document {code} not found")
    
    with open(full_path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    
    def generate():
        """스트리밍 생성기"""
        for chunk in chunk_processor.chunk_document(doc.get('content', ''), chunk_tokens):
            yield json.dumps(chunk, ensure_ascii=False) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )

# 헬퍼 함수들
def _extract_sections(content: str) -> List[Dict[str, Any]]:
    """섹션 추출"""
    sections = []
    pattern = r'^(\d+\.?\d*)\s+(.+?)$'
    
    lines = content.split('\n')
    current_section = None
    section_content = []
    
    for i, line in enumerate(lines):
        match = re.match(pattern, line, re.MULTILINE)
        if match:
            if current_section:
                sections.append({
                    'id': current_section['id'],
                    'title': current_section['title'],
                    'start_line': current_section['start'],
                    'end_line': i,
                    'content_preview': '\n'.join(section_content[:5]),
                    'tokens': len('\n'.join(section_content)) // 3
                })
            
            current_section = {
                'id': match.group(1),
                'title': match.group(2),
                'start': i
            }
            section_content = []
        else:
            section_content.append(line)
    
    if current_section:
        sections.append({
            'id': current_section['id'],
            'title': current_section['title'],
            'start_line': current_section['start'],
            'end_line': len(lines),
            'content_preview': '\n'.join(section_content[:5]),
            'tokens': len('\n'.join(section_content)) // 3
        })
    
    return sections[:20]

def _extract_formulas(content: str) -> List[Dict[str, Any]]:
    """수식 추출"""
    formulas = []
    
    math_patterns = [
        r'\$\$(.+?)\$\$',  # Display math
        r'\$(.+?)\$',      # Inline math
        r'\\begin\{equation\}(.+?)\\end\{equation\}',
        r'식\s*\((\d+\.?\d*)\)',  # 한글 수식 번호
    ]
    
    for pattern in math_patterns:
        matches = re.finditer(pattern, content, re.DOTALL)
        for match in matches:
            formulas.append({
                'formula': match.group(1) if len(match.groups()) > 0 else match.group(0),
                'position': match.start(),
                'context': content[max(0, match.start()-50):match.end()+50]
            })
    
    return formulas[:20]

def _extract_tables(content: str) -> List[Dict[str, Any]]:
    """표 추출"""
    tables = []
    
    table_patterns = [
        r'표\s*(\d+\.?\d*)',
        r'Table\s*(\d+\.?\d*)',
        r'<표\s*(\d+\.?\d*)>',
    ]
    
    for pattern in table_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            tables.append({
                'table_id': match.group(1),
                'position': match.start(),
                'context': content[max(0, match.start()-100):match.start()+200]
            })
    
    return tables[:20]

def _extract_relevant_content(content: str, keywords: list, sections: list) -> str:
    """관련 내용 추출"""
    relevant_parts = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw.lower() in line_lower for kw in keywords):
            start = max(0, i - 5)
            end = min(len(lines), i + 10)
            relevant_parts.append('\n'.join(lines[start:end]))
    
    return '\n\n---\n\n'.join(relevant_parts[:10])

def _create_topic_summary(topic: str, content: str) -> str:
    """주제별 요약 생성"""
    templates = {
        '정착길이': """철근의 정착길이는 철근이 콘크리트에 충분히 묻혀 있어 
설계 응력을 안전하게 전달할 수 있는 최소 길이입니다. 
기본 정착길이는 철근 직경, 콘크리트 강도, 철근 위치 등에 따라 결정됩니다.""",
        
        '이음길이': """철근의 이음길이는 두 철근이 겹쳐져 응력을 전달하는 데 
필요한 최소 길이입니다. 이음길이는 정착길이보다 길게 설계되며, 
철근 간격과 위치에 따라 보정계수가 적용됩니다.""",
        
        '피복두께': """콘크리트 피복두께는 철근 표면에서 콘크리트 표면까지의 
최단거리로, 철근의 부식 방지와 내화성능 확보를 위해 필요합니다.""",
        
        '전단': """전단설계는 보와 슬래브에서 전단력에 저항하기 위한 
철근 배치를 결정하는 과정입니다. 콘크리트의 전단강도와 
전단철근의 기여를 고려하여 설계합니다.""",
        
        '균열': """균열제어는 콘크리트 구조물의 사용성을 확보하기 위해 
균열폭을 제한하는 설계 과정입니다. 철근 간격과 피복두께가 
주요 설계변수입니다."""
    }
    
    base_summary = templates.get(topic, "관련 내용 요약")
    
    # 실제 내용에서 핵심 문장 추출
    key_sentences = []
    for line in content.split('\n'):
        if len(line) > 20 and any(kw in line for kw in ['기준', '이상', '이하', 'mm']):
            key_sentences.append(line.strip())
    
    if key_sentences:
        base_summary += "\n\n주요 규정:\n" + '\n'.join(key_sentences[:3])
    
    return base_summary

def _extract_key_points(content: str) -> List[str]:
    """핵심 포인트 추출"""
    key_points = []
    
    number_pattern = r'(\d+\.?\d*)\s*(mm|MPa|m|cm)'
    
    for line in content.split('\n'):
        if re.search(number_pattern, line):
            key_points.append(line.strip())
    
    return key_points[:5]

def _extract_topic_formulas(content: str) -> List[str]:
    """주제 관련 수식 추출"""
    formulas = []
    
    formula_patterns = [
        r'[lL]_?d\s*=',  # 정착길이
        r'[lL]_?s\s*=',  # 이음길이
        r'=\s*\d+\.?\d*\s*[×x]\s*d_?b',  # 직경 배수
    ]
    
    for pattern in formula_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            
            formula_line = content[line_start:line_end].strip()
            formulas.append(formula_line)
    
    return formulas[:3]

def _extract_topic_tables(content: str) -> List[str]:
    """주제 관련 표 추출"""
    tables = []
    
    table_patterns = ['표', 'Table']
    for pattern in table_patterns:
        if pattern in content:
            for line in content.split('\n'):
                if pattern in line and len(line) < 100:
                    tables.append(line.strip())
    
    return tables[:3]

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