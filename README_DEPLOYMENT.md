# 한국 건설표준 GPT API 배포 가이드

## 🎯 개요
한국 건설표준(KDS/KCS/EXCS) 5,233개 문서를 활용한 GPT API를 Render.com에 무료로 배포하는 가이드입니다.

## 📋 준비사항
- Python 3.8+ 설치
- Git 설치 (선택사항)
- Render.com 계정
- ChatGPT Plus 계정

## 🚀 자동 배포 (권장)

### Windows 사용자
```cmd
# gpts_data 폴더로 이동
cd gpts_data

# 배치 스크립트 실행
deploy_to_render.bat
```

### Linux/Mac 사용자
```bash
# gpts_data 폴더로 이동
cd gpts_data

# Python 스크립트 실행
python auto_deploy_render.py
```

## 🔧 수동 배포

### 1. Render.com 서비스 생성
1. [Render.com](https://render.com) 접속 및 계정 생성
2. "New +" → "Web Service" 선택
3. GitHub 저장소 연결 또는 수동 업로드

### 2. 서비스 설정
```yaml
Name: kcsc-gpt-api
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python lightweight_gpts_api_server.py
Plan: Free
Auto-Deploy: Yes
```

### 3. 환경 변수 설정
```
API_KEY=kcsc-gpt-secure-key-2025
PORT=10000
LOG_LEVEL=INFO
```

### 4. 파일 업로드
다음 파일들을 Render에 업로드:
- `lightweight_gpts_api_server.py`
- `requirements.txt`
- `render.yaml`
- `search_index.json`
- `kcsc_*.json` (모든 데이터 파일)

## 🧪 배포 테스트

### Health Check
```bash
curl https://your-app-name.onrender.com/health
```

### API 테스트
```bash
curl -X POST https://your-app-name.onrender.com/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: kcsc-gpt-secure-key-2025" \
  -d '{"query": "콘크리트", "search_type": "keyword", "limit": 5}'
```

## 🤖 GPT 설정

### 1. ChatGPT Plus에서 GPT 생성
1. https://chat.openai.com 접속
2. "Explore" → "Create a GPT" 선택

### 2. 기본 정보
- **Name:** 한국 건설표준 AI 전문가
- **Description:** 한국 건설표준(KDS/KCS/EXCS) 5,233개 문서에 정통한 건설 분야 AI 전문가

### 3. Instructions
`GPTs_INSTRUCTIONS.md` 파일의 내용을 복사하여 붙여넣기

### 4. Actions 설정
- **Import from URL:** `https://your-app-name.onrender.com/openapi.json`
- **Authentication:** API Key
- **API Key:** `kcsc-gpt-secure-key-2025`
- **Auth Type:** Custom
- **Header Name:** `X-API-Key`

### 5. Knowledge 파일 업로드 (순서대로)
1. `search_index.json` (필수)
2. `kcsc_structure.json`
3. `kcsc_civil.json`
4. `kcsc_building.json`
5. `kcsc_facility.json`
6. `kcsc_excs.json`
7. `kcsc_high_quality_part1.json`
8. `kcsc_high_quality_part2.json`
9. `kcsc_high_quality_part3.json`

**주의:** 총 용량 512MB 제한

### 6. Conversation Starters
- KCS 14 20 01의 내용을 알려줘
- 콘크리트 압축강도 시험 방법은?
- 지반조사 관련 표준을 알려줘
- 시공 순서도 생성해줘

## 📊 모니터링

### API 통계 확인
```
GET https://your-app-name.onrender.com/api/v1/stats
Header: X-API-Key: kcsc-gpt-secure-key-2025
```

### Render 대시보드
- 로그 확인
- 메트릭스 모니터링
- 배포 상태 확인

## 🔧 문제 해결

### 일반적인 문제
1. **API 연결 실패**
   - Render 서비스 상태 확인
   - API 키 확인
   - CORS 설정 확인

2. **검색 결과 없음**
   - 데이터 파일 업로드 확인
   - 인덱스 파일 로드 상태 확인

3. **응답 속도 느림**
   - 무료 플랜의 콜드 스타트 현상
   - 첫 요청 시 지연 정상

### 로그 확인
```bash
# Render 대시보드에서 로그 확인
# 또는 API를 통한 상태 확인
curl https://your-app-name.onrender.com/health
```

## 📈 성능 최적화

### 메모리 사용량 최적화
- 필요한 데이터 파일만 로드
- 캐싱 활용
- 검색 인덱스 최적화

### 응답 속도 개선
- 검색 알고리즘 최적화
- 결과 제한 설정
- 압축 활용

## 🔒 보안 고려사항

### API 키 관리
- 환경 변수 사용
- 정기적인 키 교체
- 접근 로그 모니터링

### CORS 설정
- OpenAI 도메인만 허용
- 필요한 헤더만 허용

## 📞 지원

### 문서 및 리소스
- [Render.com 문서](https://render.com/docs)
- [OpenAI GPT Actions 가이드](https://platform.openai.com/docs/actions)
- [FastAPI 문서](https://fastapi.tiangolo.com/)

### 커뮤니티
- GitHub Issues
- 개발자 포럼
- 기술 블로그

---

## 🎉 완료!
배포가 성공적으로 완료되면 다음과 같은 결과를 얻을 수 있습니다:

✅ **API 서버**: https://your-app-name.onrender.com  
✅ **GPT 봇**: ChatGPT에서 사용 가능한 전문 건설 AI  
✅ **검색 기능**: 5,233개 건설표준 문서 검색  
✅ **무료 호스팅**: Render.com 무료 플랜 활용  

이제 한국 건설표준에 대한 전문적인 질문을 GPT에게 물어보세요!