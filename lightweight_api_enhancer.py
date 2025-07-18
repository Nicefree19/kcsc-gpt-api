"""
GPT를 위한 경량화 API 엔드포인트 추가
토큰 제한을 고려한 스마트 응답 시스템
"""

from typing import Dict, List, Optional, Any
import json
import re
from collections import defaultdict

class TokenCounter:
    """간단한 토큰 카운터 (근사치)"""
    @staticmethod
    def count(text: str) -> int:
        # 한글은 평균 2토큰, 영문은 0.75토큰으로 계산
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        numbers = len(re.findall(r'\d+', text))
        
        return korean_chars * 2 + english_words + numbers + len(text) // 10

class SmartSummarizer:
    """계층적 요약 생성기"""
    
    def __init__(self, token_limits: Dict[str, int] = None):
        self.token_limits = token_limits or {
            'micro': 50,      # 제목 + 한줄
            'mini': 200,      # 핵심 요약
            'summary': 500,   # 일반 요약
            'detail': 2000,   # 상세 내용
            'full': 5000      # 전체 (청크)
        }
        self.counter = TokenCounter()
    
    def create_micro_summary(self, doc: Dict) -> Dict:
        """초경량 요약 (50 토큰)"""
        title = doc.get('title', '')
        code = doc.get('id', '')
        category = doc.get('category', '')
        
        return {
            'level': 'micro',
            'tokens': 50,
            'content': f"{code} - {title[:30]}",
            'category': category
        }
    
    def create_mini_summary(self, doc: Dict) -> Dict:
        """미니 요약 (200 토큰)"""
        content = doc.get('content', {})
        if isinstance(content, dict):
            full_text = content.get('full', '')
        else:
            full_text = str(content)
        
        # 첫 200자 추출
        summary = full_text[:200].strip()
        if len(full_text) > 200:
            summary += "..."
        
        return {
            'level': 'mini',
            'tokens': self.counter.count(summary),
            'content': summary,
            'metadata': doc.get('metadata', {})
        }
    
    def create_smart_summary(self, doc: Dict, query: str = None) -> Dict:
        """질문 기반 스마트 요약"""
        if not query:
            return self.create_mini_summary(doc)
        
        # 질문 키워드 추출
        keywords = self.extract_keywords(query)
        
        # 관련 섹션 찾기
        relevant_sections = self.find_relevant_sections(doc, keywords)
        
        # 토큰 예산 내에서 요약 생성
        summary = self.build_query_focused_summary(relevant_sections, 1000)
        
        return {
            'level': 'smart',
            'tokens': self.counter.count(summary),
            'content': summary,
            'keywords_found': keywords,
            'sections_used': [s['title'] for s in relevant_sections[:3]]
        }
    
    def extract_keywords(self, query: str) -> List[str]:
        """질문에서 핵심 키워드 추출"""
        # 불용어 제거
        stopwords = {'은', '는', '이', '가', '을', '를', '의', '에', '에서', '으로', '와', '과'}
        
        # 키워드 추출
        words = re.findall(r'[가-힣]+|[a-zA-Z]+|\d+', query)
        keywords = [w for w in words if w not in stopwords and len(w) > 1]
        
        # 전문 용어 우선순위
        priority_terms = ['균열', '철근', '콘크리트', '강도', '하중', '안전율', '계산', '공식']
        
        # 우선순위 정렬
        keywords.sort(key=lambda x: 0 if x in priority_terms else 1)
        
        return keywords[:5]  # 상위 5개만
    
    def find_relevant_sections(self, doc: Dict, keywords: List[str]) -> List[Dict]:
        """키워드 관련 섹션 찾기"""
        sections = []
        content = doc.get('content', {})
        
        if isinstance(content, dict) and 'sections' in content:
            for section in content['sections']:
                score = 0
                section_text = section.get('content', '').lower()
                
                for keyword in keywords:
                    if keyword.lower() in section_text:
                        score += section_text.count(keyword.lower())
                
                if score > 0:
                    sections.append({
                        'title': section.get('title', ''),
                        'content': section.get('content', ''),
                        'score': score
                    })
        
        # 점수순 정렬
        sections.sort(key=lambda x: x['score'], reverse=True)
        return sections
    
    def build_query_focused_summary(self, sections: List[Dict], token_limit: int) -> str:
        """질문 중심 요약 생성"""
        summary_parts = []
        current_tokens = 0
        
        for section in sections:
            # 섹션 요약
            section_summary = f"[{section['title']}] {section['content'][:200]}..."
            section_tokens = self.counter.count(section_summary)
            
            if current_tokens + section_tokens <= token_limit:
                summary_parts.append(section_summary)
                current_tokens += section_tokens
            else:
                break
        
        return "\n\n".join(summary_parts)

class QueryIntentAnalyzer:
    """질문 의도 분석기"""
    
    def __init__(self):
        self.intent_patterns = {
            'definition': {
                'patterns': ['무엇', '뭐야', '뭔가요', 'what is', '정의'],
                'required_depth': 'mini',
                'sections': ['개요', '정의', '일반사항']
            },
            'calculation': {
                'patterns': ['계산', '공식', '수식', 'formula', '구하는'],
                'required_depth': 'detail',
                'sections': ['계산', '공식', '설계']
            },
            'requirement': {
                'patterns': ['기준', '규정', '조건', '요구사항', 'requirement'],
                'required_depth': 'summary',
                'sections': ['기준', '규정', '요구사항']
            },
            'procedure': {
                'patterns': ['방법', '절차', '어떻게', 'how to', '순서'],
                'required_depth': 'detail',
                'sections': ['시공', '절차', '방법']
            },
            'comparison': {
                'patterns': ['차이', '비교', 'vs', '다른', 'difference'],
                'required_depth': 'summary',
                'sections': ['비교', '차이점']
            }
        }
    
    def analyze(self, query: str) -> Dict:
        """질문 의도 분석"""
        query_lower = query.lower()
        detected_intents = []
        
        for intent, config in self.intent_patterns.items():
            for pattern in config['patterns']:
                if pattern in query_lower:
                    detected_intents.append({
                        'type': intent,
                        'confidence': 0.8,
                        'required_depth': config['required_depth'],
                        'target_sections': config['sections']
                    })
                    break
        
        # 기본값
        if not detected_intents:
            detected_intents.append({
                'type': 'general',
                'confidence': 0.5,
                'required_depth': 'summary',
                'target_sections': []
            })
        
        return detected_intents[0]

class LightweightResponseBuilder:
    """경량화 응답 생성기"""
    
    def __init__(self):
        self.summarizer = SmartSummarizer()
        self.analyzer = QueryIntentAnalyzer()
        self.counter = TokenCounter()
    
    def build_response(self, doc: Dict, query: str = None, max_tokens: int = 2000) -> Dict:
        """토큰 제한을 고려한 응답 생성"""
        
        # 1. 질문 의도 분석
        intent = self.analyzer.analyze(query) if query else {'required_depth': 'summary'}
        
        # 2. 기본 정보 (항상 포함)
        response = {
            'code': doc.get('id', ''),
            'title': doc.get('title', ''),
            'intent': intent['type'] if query else 'browse',
            'tokens_used': 0,
            'max_tokens': max_tokens
        }
        
        # 3. 레벨별 컨텐츠 추가
        contents = []
        
        # Level 1: 마이크로 요약 (항상)
        micro = self.summarizer.create_micro_summary(doc)
        contents.append(micro)
        response['tokens_used'] += micro['tokens']
        
        # Level 2: 의도에 따른 요약
        if response['tokens_used'] < max_tokens - 500:
            if query:
                summary = self.summarizer.create_smart_summary(doc, query)
            else:
                summary = self.summarizer.create_mini_summary(doc)
            
            if response['tokens_used'] + summary['tokens'] <= max_tokens:
                contents.append(summary)
                response['tokens_used'] += summary['tokens']
        
        # Level 3: 추가 섹션 (여유가 있으면)
        if intent['required_depth'] == 'detail' and response['tokens_used'] < max_tokens - 1000:
            # 관련 섹션 추가
            sections = self.summarizer.find_relevant_sections(doc, intent['target_sections'])
            for section in sections[:2]:  # 최대 2개 섹션
                section_tokens = self.counter.count(section['content'])
                if response['tokens_used'] + section_tokens <= max_tokens:
                    contents.append({
                        'level': 'section',
                        'title': section['title'],
                        'tokens': section_tokens,
                        'content': section['content'][:500]
                    })
                    response['tokens_used'] += section_tokens
        
        response['contents'] = contents
        
        # 4. 네비게이션 정보
        response['navigation'] = {
            'has_more': len(str(doc.get('content', ''))) > response['tokens_used'] * 3,
            'available_sections': self._get_available_sections(doc),
            'suggested_next': self._suggest_next_action(intent, response['tokens_used'], max_tokens)
        }
        
        return response
    
    def _get_available_sections(self, doc: Dict) -> List[str]:
        """사용 가능한 섹션 목록"""
        # 실제 구현에서는 문서 구조 파싱
        return ['1. 일반사항', '2. 재료', '3. 설계', '4. 시공', '5. 품질관리']
    
    def _suggest_next_action(self, intent: Dict, used: int, max_tokens: int) -> str:
        """다음 액션 제안"""
        if used > max_tokens * 0.8:
            return "토큰 한계 근접. 특정 섹션 요청 권장"
        elif intent['required_depth'] == 'detail' and used < max_tokens * 0.5:
            return "추가 상세 정보 요청 가능"
        else:
            return "현재 정보로 충분. 필요시 특정 부분 요청"

# API 통합을 위한 헬퍼 함수
def create_lightweight_endpoints(app, documents_cache):
    """경량화 엔드포인트 추가"""
    
    response_builder = LightweightResponseBuilder()
    
    @app.get("/api/v2/lightweight/{code}")
    async def get_lightweight(
        code: str, 
        query: Optional[str] = None,
        max_tokens: int = 2000
    ):
        """경량화된 응답"""
        normalized_code = normalize_code(code)
        
        if normalized_code not in documents_cache:
            return {"error": f"Document {normalized_code} not found"}
        
        doc = documents_cache[normalized_code]
        return response_builder.build_response(doc, query, max_tokens)
    
    @app.get("/api/v2/summary/{code}")
    async def get_tiered_summary(
        code: str,
        level: str = "mini"  # micro, mini, summary, detail
    ):
        """계층별 요약"""
        normalized_code = normalize_code(code)
        
        if normalized_code not in documents_cache:
            return {"error": f"Document {normalized_code} not found"}
        
        doc = documents_cache[normalized_code]
        summarizer = SmartSummarizer()
        
        if level == "micro":
            return summarizer.create_micro_summary(doc)
        elif level == "mini":
            return summarizer.create_mini_summary(doc)
        else:
            return summarizer.create_mini_summary(doc)  # 기본값
    
    @app.post("/api/v2/smart-query")
    async def smart_query(request: Dict):
        """스마트 쿼리 처리"""
        code = request.get('code')
        query = request.get('query')
        max_tokens = request.get('max_tokens', 3000)
        
        normalized_code = normalize_code(code)
        
        if normalized_code not in documents_cache:
            return {"error": f"Document {normalized_code} not found"}
        
        doc = documents_cache[normalized_code]
        return response_builder.build_response(doc, query, max_tokens)
    
    return app

# 사용 예시
if __name__ == "__main__":
    # 테스트
    test_doc = {
        'id': 'KDS 14 20 52',
        'title': '콘크리트구조 균열 제어 설계기준',
        'content': {
            'full': '매우 긴 내용...' * 1000
        }
    }
    
    builder = LightweightResponseBuilder()
    
    # 일반 요청
    response1 = builder.build_response(test_doc, max_tokens=500)
    print(f"일반 응답: {response1['tokens_used']} tokens")
    
    # 질문 기반 요청
    response2 = builder.build_response(test_doc, "균열폭 계산 방법", max_tokens=2000)
    print(f"질문 응답: {response2['tokens_used']} tokens")