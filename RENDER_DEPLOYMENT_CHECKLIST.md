# Render 배포 체크리스트

## 🔍 배포 전 확인사항

### 필수 파일 존재 여부
- [ ] `search_index.json` - 검색 인덱스
- [ ] `standards_split/split_index.json` - 분할 인덱스
- [ ] `render_ready_api_server.py` - 메인 API 서버
- [ ] `requirements.txt` - 의존성 목록
- [ ] `render.yaml` - Render 설정

### 환경 변수 설정
- [ ] `API_KEY=kcsc-gpt-secure-key-2025`
- [ ] `LOG_LEVEL=INFO`
- [ ] `PORT=10000` (Render가 자동 설정)

## 🚀 배포 과정

### 1. 로컬 테스트
```bash
# 경로 수정 실행
python fix_render_paths.py

# 로컬 서버 테스트
python render_ready_api_server.py
```

### 2. Git 업로드
```bash
git add .
git commit -m "Fix Render deployment issues"
git push origin main
```

### 3. Render 배포
- Render 대시보드에서 Manual Deploy 클릭
- 빌드 로그 확인
- 배포 완료 후 헬스 체크

## 🔧 문제 해결

### 일반적인 오류와 해결책

#### 1. "Search index not found" 오류
**원인**: `search_index.json` 파일 누락
**해결**: `fix_render_paths.py` 실행으로 자동 생성

#### 2. "Split index not found" 오류  
**원인**: `standards_split/split_index.json` 경로 문제
**해결**: 새로운 API 서버가 자동으로 다중 경로 검색

#### 3. "Module not found" 오류
**원인**: `requirements.txt` 의존성 누락
**해결**: 필요한 패키지 추가

#### 4. "Port already in use" 오류
**원인**: 포트 충돌
**해결**: Render가 자동으로 PORT 환경변수 설정

## 📊 성공 지표

### 배포 성공 시 로그
```
✅ Search index loaded from /opt/render/project/src/search_index.json
✅ Split index loaded from /opt/render/project/src/standards_split/split_index.json
🚀 Starting Render-ready API server...
✅ Server ready!
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
```

### API 응답 테스트
```bash
# 헬스 체크 (200 OK 응답 확인)
curl https://your-app.onrender.com/health

# 검색 기능 (정상 JSON 응답 확인)
curl -X POST "https://your-app.onrender.com/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "콘크리트"}'
```

## 🎯 최적화 팁

### 성능 개선
- 캐싱 활용으로 응답 속도 향상
- 불필요한 로그 레벨 조정
- 메모리 사용량 모니터링

### 보안 강화
- API 키 검증 활성화
- CORS 설정 최적화
- 요청 제한 설정

### 모니터링
- 헬스 체크 엔드포인트 활용
- 로그 레벨 적절히 설정
- 오류 발생 시 알림 설정

## 📞 지원

문제 발생 시:
1. Render 빌드 로그 확인
2. API 엔드포인트 직접 테스트
3. 로컬 환경에서 재현 시도
4. 필요시 롤백 후 재배포