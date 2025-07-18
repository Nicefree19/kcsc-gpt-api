# GPT 대용량 문서 처리 가이드

## 개요
한국 건설표준 문서(KDS/KCS)는 평균 2-5만 토큰의 대용량 문서입니다. GPT의 토큰 제한(8K)을 극복하기 위해 다양한 경량화 API를 제공합니다.

## 주요 API 엔드포인트

### 1. 청크 기반 문서 접근
```
GET /api/v2/standard/{code}/chunked
```
- **용도**: 대용량 문서를 작은 조각으로 나누어 접근
- **파라미터**:
  - `chunk_size`: 청크당 토큰 수 (기본: 1000)
  - `query`: 검색어 (해당 내용 우선 반환)
  - `start_chunk`: 시작 청크 번호
- **예시**: `/api/v2/standard/KDS 14 20 52/chunked?query=정착길이&chunk_size=500`

### 2. 섹션 인덱스 조회
```
GET /api/v2/standard/{code}/section-index
```
- **용도**: 문서의 구조와 섹션 정보 빠른 확인
- **반환**: 섹션 목록, 수식/표 위치, 주요 섹션 정보
- **예시**: `/api/v2/standard/KDS 14 20 52/section-index`

### 3. 주제별 요약
```
GET /api/v2/standard/{code}/topic/{topic}
```
- **용도**: 자주 묻는 주제에 대한 사전 요약
- **지원 주제**: 정착길이, 이음길이, 피복두께, 전단, 균열
- **예시**: `/api/v2/standard/KDS 14 20 52/topic/정착길이`

### 4. 스트리밍 응답
```
GET /api/v2/standard/{code}/stream
```
- **용도**: 실시간으로 문서 내용 스트리밍
- **파라미터**: `chunk_tokens` (청크당 토큰)
- **형식**: NDJSON (Newline Delimited JSON)

## 사용 시나리오

### 시나리오 1: 특정 내용 찾기
사용자가 "KDS 14 20 52의 정착길이 계산식"을 묻는 경우:

1. 먼저 주제별 요약 확인:
   ```
   GET /api/v2/standard/KDS 14 20 52/topic/정착길이
   ```

2. 더 자세한 내용이 필요하면 청크 검색:
   ```
   GET /api/v2/standard/KDS 14 20 52/chunked?query=정착길이 계산
   ```

### 시나리오 2: 문서 전체 구조 파악
1. 섹션 인덱스 조회:
   ```
   GET /api/v2/standard/KDS 14 20 52/section-index
   ```

2. 특정 섹션만 청크로 가져오기:
   ```
   GET /api/v2/standard/KDS 14 20 52/chunked?query=3.2 철근의 정착
   ```

### 시나리오 3: 점진적 로딩
1. 첫 번째 청크 요청:
   ```
   GET /api/v2/standard/KDS 14 20 52/chunked?start_chunk=0
   ```

2. 다음 청크 요청:
   ```
   GET /api/v2/standard/KDS 14 20 52/chunked?start_chunk=3
   ```

## 응답 형식

### 청크 응답
```json
{
  "code": "KDS 14 20 52",
  "query": "정착길이",
  "total_chunks": 15,
  "current_chunk": 0,
  "chunks": [
    {
      "chunk_index": 0,
      "relevance": "high",
      "content": "3.2 철근의 정착길이...",
      "tokens": 850,
      "has_more": true
    }
  ],
  "next_chunk": 1,
  "completed": false
}
```

### 주제 요약 응답
```json
{
  "code": "KDS 14 20 52",
  "topic": "정착길이",
  "title": "콘크리트구조 정착 및 이음 설계기준 - 정착길이",
  "summary": "철근의 정착길이는...",
  "key_points": [
    "기본 정착길이는 300mm 이상",
    "D19 이하 철근: ld = 0.9 × db × fy / √fck"
  ],
  "formulas": ["ld = 0.9 × db × fy / √fck"],
  "tokens": 450
}
```

## 최적화 팁

1. **캐싱 활용**: 자주 조회되는 주제는 `/topic/` 엔드포인트 사용
2. **쿼리 최적화**: 구체적인 검색어로 관련 청크만 가져오기
3. **점진적 로딩**: 필요한 만큼만 청크 요청
4. **섹션 인덱스**: 먼저 구조 파악 후 필요한 부분만 접근

## 에러 처리

- **404 Not Found**: 문서가 없거나 잘못된 코드 형식
- **400 Bad Request**: 잘못된 파라미터
- **토큰 초과**: 자동으로 청크 분할되므로 걱정 없음

## GPT Instructions 추가 예시

```
한국 건설표준 문서는 대용량이므로 다음 전략을 사용하세요:

1. 특정 주제 질문: /api/v2/standard/{code}/topic/{topic} 사용
2. 검색이 필요한 경우: /api/v2/standard/{code}/chunked?query={keyword}
3. 문서 구조 파악: /api/v2/standard/{code}/section-index
4. 청크 단위로 점진적 로딩: start_chunk 파라미터 활용

예: "KDS 14 20 52의 정착길이는?"
→ GET /api/v2/standard/KDS 14 20 52/topic/정착길이
```