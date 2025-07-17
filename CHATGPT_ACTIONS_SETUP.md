# 🤖 ChatGPT GPT Actions 완전 설정 가이드

## 📋 현재 상황
- ✅ GitHub 저장소 커밋 완료
- ✅ Render 배포 준비 완료  
- 🔄 ChatGPT GPT Actions 설정 진행 중

## 🔧 Actions 설정 단계별 가이드

### 1️⃣ 스키마 설정 (현재 화면)

## 🔧 Actions 스키마 설정 방법

### 방법 1: URL에서 가져오기 (권장)
```
https://kcsc-gpt-api.onrender.com/openapi.json
```

### 방법 2: 스키마 직접 복사 (현재 오류 해결용)
아래 JSON 스키마를 복사하여 붙여넣기:

```yaml
openapi: 3.0.0
info:
  title: Korean Construction Standards API
  description: 한국 건설표준(KDS/KCS/EXCS) 검색 및 조회 API - 5,233개 문서 지원
  version: 1.0.0
servers:
  - url: https://kcsc-gpt-api.onrender.com
    description: Production server

paths:
  /api/v1/search:
    post:
      operationId: searchStandards
      summary: 건설표준 검색
      description: 코드, 키워드, 카테고리로 건설표준 검색
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - query
              properties:
                query:
                  type: string
                  description: 검색어 (표준코드, 키워드, 카테고리명)
                  example: "콘크리트 압축강도"
                search_type:
                  type: string
                  enum: ["keyword", "code", "category"]
                  default: "keyword"
                  description: 검색 유형
                limit:
                  type: integer
                  minimum: 1
                  maximum: 50
                  default: 10
                  description: 결과 개수 제한
      responses:
        '200':
          description: 검색 성공
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      results:
                        type: array
                        items:
                          type: object
                          properties:
                            code:
                              type: string
                              description: 표준 코드
                            title:
                              type: string
                              description: 표준 제목
                            content:
                              type: string
                              description: 표준 내용 요약
                            relevance_score:
                              type: number
                              description: 관련도 점수
                            metadata:
                              type: object
                              description: 메타데이터
                      total:
                        type: integer
                        description: 총 결과 수
                  timestamp:
                    type: string
                    format: date-time

  /api/v1/standard/{code}:
    get:
      operationId: getStandardDetail
      summary: 표준 상세 조회
      description: 특정 표준의 상세 내용 조회
      parameters:
        - name: code
          in: path
          required: true
          schema:
            type: string
          description: 표준 코드 (예 KCS 14 20 01)
          example: "KCS 14 20 01"
      responses:
        '200':
          description: 조회 성공
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      code:
                        type: string
                        description: 표준 코드
                      title:
                        type: string
                        description: 표준 제목
                      full_content:
                        type: string
                        description: 전체 내용
                      sections:
                        type: object
                        description: 섹션별 내용
                      metadata:
                        type: object
                        description: 메타데이터
                      related_standards:
                        type: array
                        items:
                          type: string
                        description: 관련 표준 목록
                  timestamp:
                    type: string
                    format: date-time

  /api/v1/keywords:
    get:
      operationId: getKeywords
      summary: 키워드 목록 조회
      description: 검색 가능한 키워드 목록 조회
      parameters:
        - name: prefix
          in: query
          schema:
            type: string
          description: 키워드 접두사 필터
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 50
          description: 결과 개수 제한
      responses:
        '200':
          description: 조회 성공

  /api/v1/stats:
    get:
      operationId: getStatistics
      summary: 통계 정보 조회
      description: 시스템 통계 및 상태 정보 조회
      responses:
        '200':
          description: 조회 성공

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: API 키 인증

security:
  - ApiKeyAuth: []
```

### 2️⃣ Authentication 설정

**인증 방식:**
- **Type**: API Key
- **API Key**: `kcsc-gpt-secure-key-2025`
- **Auth Type**: Custom
- **Custom Header Name**: `X-API-Key`

### 3️⃣ Privacy Policy (선택사항)
```
이 GPT는 한국 건설표준 문서 검색을 위해 공개된 표준 정보만을 사용합니다. 
개인정보는 수집하지 않으며, 모든 데이터는 공개된 건설표준 문서에서 추출됩니다.
```

## 🧪 Actions 테스트 방법

### 테스트 1: 키워드 검색
```json
{
  "query": "콘크리트 압축강도",
  "search_type": "keyword",
  "limit": 5
}
```

### 테스트 2: 코드 검색
```json
{
  "query": "KCS 14 20 01",
  "search_type": "code",
  "limit": 1
}
```

### 테스트 3: 카테고리 검색
```json
{
  "query": "지반",
  "search_type": "category",
  "limit": 10
}
```

## 🎯 완성 후 테스트 질문

GPT 설정이 완료되면 다음 질문들로 테스트해보세요:

```
"KCS 14 20 01의 내용을 알려줘"
"콘크리트 압축강도 시험 방법은?"
"지반조사 관련 표준을 알려줘"
"터널 굴착 시 안전 기준은?"
"시공 순서도를 생성해줘"
```

## 🔧 문제 해결

### Actions 연결 실패 시
1. **URL 확인**: https://kcsc-gpt-api.onrender.com/openapi.json 접속 가능한지 확인
2. **API Key 확인**: `kcsc-gpt-secure-key-2025` 정확히 입력
3. **Header Name 확인**: `X-API-Key` (대소문자 구분)

### API 응답 없음 시
1. **Render 서비스 상태**: https://dashboard.render.com 에서 서비스 상태 확인
2. **Health Check**: https://kcsc-gpt-api.onrender.com/health 접속 테스트
3. **콜드 스타트**: 첫 요청 시 30초 정도 지연 가능 (무료 플랜)

## 🎉 완성!

Actions 설정이 완료되면:
- ✅ 5,233개 건설표준 문서 검색 가능
- ✅ 실시간 API 연동으로 최신 정보 제공
- ✅ 전문적인 건설 기술 상담 가능
- ✅ 표준 간 교차 참조 및 비교 분석

**이제 한국 건설 분야의 전문 AI 어시스턴트가 완성되었습니다!** 🏗️✨