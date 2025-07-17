# GPT Actions 설정 가이드

## 1. API 서버 확인

먼저 Render에 배포된 API 서버가 정상 작동하는지 확인:
```
https://kcsc-gpt-api.onrender.com/health
```

## 2. GPT Actions 설정

### 2.1 Schema 등록

1. GPT Editor에서 "Configure" 클릭
2. "Add actions" 클릭
3. "Import from URL" 또는 "Paste Schema" 선택

#### 옵션 A: URL로 가져오기
```
https://kcsc-gpt-api.onrender.com/openapi.json
```

#### 옵션 B: 수동으로 붙여넣기
`gpt_actions_simple_schema.json` 파일의 내용을 복사해서 붙여넣기

### 2.2 Authentication 설정

1. Authentication 섹션에서 "API Key" 선택
2. Auth Type: "API Key"
3. API Key 입력: Render 환경변수에 설정한 API_KEY 값

### 2.3 Privacy Policy URL (선택사항)
```
https://example.com/privacy
```

## 3. GPT Instructions 예시

```
당신은 한국 건설표준(KDS/KCS) 전문가 AI 어시스턴트입니다.

주요 기능:
1. 건설표준 검색: 키워드, 코드, 카테고리로 검색
2. 상세 정보 제공: 특정 표준의 전체 내용 확인
3. 섹션별 조회: 큰 문서는 섹션별로 나누어 조회

사용 가능한 Actions:
- searchStandards: 표준 검색
- getStandardDetail: 표준 상세 조회 (작은 문서)
- getStandardSummary: 표준 요약 조회
- getStandardSection: 특정 섹션 조회 (큰 문서)

응답 시 참고사항:
- KDS: 설계기준 (Korea Design Standard)
- KCS: 시공기준 (Korea Construction Standard)
- 코드 형식: "KCS 14 20 01" (공백 포함)
```

## 4. 테스트 예시

### 검색 테스트
```
User: "철근콘크리트 관련 표준을 찾아줘"
GPT: searchStandards(query="철근콘크리트", search_type="keyword")
```

### 상세 조회 테스트
```
User: "KCS 14 20 01 표준 내용을 보여줘"
GPT: getStandardSummary(code="KCS 14 20 01")
→ 요약 확인 후 필요시 getStandardSection 호출
```

## 5. 트러블슈팅

### "Could not find a valid URL in servers" 오류
- OpenAPI 스키마에 servers 섹션이 있는지 확인
- URL이 https://로 시작하는지 확인

### 401 Unauthorized 오류
- API Key가 올바르게 설정되었는지 확인
- Header name이 "X-API-Key"인지 확인

### ResponseTooLargeError
- 큰 문서는 summary → section → part 순으로 조회
- limit 파라미터로 검색 결과 수 제한

## 6. 환경 변수 (Render)

```
API_KEY=your-secure-api-key-here
SPLIT_DATA_PATH=/app/gpts_data/standards_split
INDEX_PATH=/app/gpts_data/search_index.json
```

## 7. API 엔드포인트 요약

| 엔드포인트 | 메소드 | 설명 |
|-----------|--------|------|
| /api/v1/search | POST | 표준 검색 |
| /api/v1/standard/{code} | GET | 전체 내용 (v1) |
| /api/v1/standard/{code}/summary | GET | 요약 (v2) |
| /api/v1/standard/{code}/section/{section} | GET | 섹션별 (v2) |
| /api/v1/standard/{code}/part/{part} | GET | 파트별 (v2) |
| /api/v1/stats | GET | 통계 정보 |