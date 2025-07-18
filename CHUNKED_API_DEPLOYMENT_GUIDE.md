# 청크 API 배포 가이드

## 변경 사항 요약

### 1. 추가된 기능
- **청크 기반 문서 처리**: 대용량 문서를 1000토큰 단위로 분할
- **섹션 인덱싱**: 문서 구조를 빠르게 파악
- **주제별 요약**: 자주 묻는 5가지 주제 사전 요약
- **스트리밍 응답**: 실시간 문서 전송

### 2. 새로운 엔드포인트
```
GET /api/v2/standard/{code}/chunked     # 청크 단위 문서
GET /api/v2/standard/{code}/section-index # 섹션 인덱스
GET /api/v2/standard/{code}/topic/{topic} # 주제별 요약
GET /api/v2/standard/{code}/stream       # 스트리밍 응답
```

### 3. 주요 개선사항
- 토큰 추정 알고리즘 (한글 2토큰, 영문 1토큰)
- 쿼리 기반 스마트 청킹
- 메모리 내 캐싱 시스템
- 코드 정규화 강화

## 배포 절차

### 1. 로컬 테스트
```bash
cd /mnt/d/00.Work_AI_Tool/06.GPTs_kcsc/gpts_data
python lightweight_gpts_api_server.py
```

### 2. API 테스트
```bash
# 청크 테스트
curl "http://localhost:8000/api/v2/standard/KDS 14 20 52/chunked?query=정착길이"

# 섹션 인덱스 테스트
curl "http://localhost:8000/api/v2/standard/KDS 14 20 52/section-index"

# 주제 요약 테스트
curl "http://localhost:8000/api/v2/standard/KDS 14 20 52/topic/정착길이"
```

### 3. GitHub 푸시
```bash
git add lightweight_gpts_api_server.py
git add GPT_LARGE_DOCUMENT_HANDLING_GUIDE.md
git add CHUNKED_API_DEPLOYMENT_GUIDE.md
git commit -m "feat: Add chunked response API for large documents"
git push origin main
```

### 4. Render 재배포
- Render 대시보드에서 자동 재배포 확인
- 또는 수동으로 "Deploy" 버튼 클릭

### 5. 프로덕션 테스트
```bash
# 청크 API 테스트
curl "https://kcsc-gpt-api.onrender.com/api/v2/standard/KDS 14 20 52/chunked" \
  -H "X-API-Key: your-api-key"

# 주제별 요약 테스트
curl "https://kcsc-gpt-api.onrender.com/api/v2/standard/KDS 14 20 52/topic/정착길이" \
  -H "X-API-Key: your-api-key"
```

## GPT Actions 스키마 업데이트

OpenAPI 스키마에 새 엔드포인트 추가 필요:
```yaml
paths:
  /api/v2/standard/{code}/chunked:
    get:
      summary: Get document in chunks
      parameters:
        - name: code
          in: path
          required: true
          schema:
            type: string
        - name: chunk_size
          in: query
          schema:
            type: integer
            default: 1000
        - name: query
          in: query
          schema:
            type: string
        - name: start_chunk
          in: query
          schema:
            type: integer
            default: 0
```

## 모니터링

### 성능 지표
- 청크 생성 시간
- 캐시 히트율
- 평균 응답 크기

### 로그 확인
```bash
# Render 로그
https://dashboard.render.com/web/srv-xxx/logs

# 청크 관련 로그 필터
grep "chunked" logs.txt
grep "topic" logs.txt
```

## 롤백 계획

문제 발생 시:
1. 이전 커밋으로 롤백
2. Render에서 이전 배포로 롤백
3. v1 엔드포인트는 영향받지 않음