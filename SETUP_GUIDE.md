# 🏗️ GPTs 건설표준 챗봇 설정 가이드

## 📁 생성된 파일

총 7개 파일, 543.33 MB

### 파일 목록
- **kcsc_structure.json**: 22.9 MB (150 documents)
- **kcsc_civil.json**: 50.24 MB (376 documents)
- **kcsc_building.json**: 61.53 MB (656 documents)
- **kcsc_facility.json**: 33.89 MB (344 documents)
- **kcsc_excs.json**: 37.54 MB (656 documents)
- **kcsc_high_quality.json**: 336.07 MB (1975 documents)
- **search_index.json**: 1.16 MB

## 🚀 GPTs 설정 방법

### 1단계: GPT 생성
1. https://chat.openai.com/gpts/editor 접속
2. "Create a GPT" 클릭
3. 이름: "한국 건설표준 AI 전문가" 입력

### 2단계: Instructions 설정
1. Configure 탭 클릭
2. Instructions에 `GPTs_INSTRUCTIONS.md` 내용 전체 복사-붙여넣기

### 3단계: Knowledge 업로드
1. Knowledge 섹션에서 "Upload files" 클릭
2. 다음 순서로 파일 업로드:
   - search_index.json (필수, 가장 먼저)
   - kcsc_structure.json
   - kcsc_civil.json
   - kcsc_building.json
   - kcsc_facility.json
   - kcsc_excs.json
   - kcsc_high_quality.json

### 4단계: Capabilities 설정
- ✅ Web Browsing (최신 정보 확인용)
- ✅ Code Interpreter (데이터 분석용)
- ❌ DALL·E Image Generation (불필요)

### 5단계: Actions 설정 (선택사항)
외부 API 서버가 준비된 경우:
1. Actions 섹션에서 "Create new action" 클릭
2. Schema에 API 명세 입력
3. Authentication 설정

### 6단계: 테스트
1. "Preview" 버튼 클릭
2. 테스트 질문 입력:
   - "KCS 14 20 01의 내용을 알려줘"
   - "콘크리트 압축강도 시험 방법은?"
   - "동절기 콘크리트 타설 주의사항"

### 7단계: 게시
1. 테스트 완료 후 "Save" 클릭
2. "Publish" 선택
3. 공유 설정 (Anyone with link 추천)

## ❗ 주의사항
- 파일 크기가 512MB를 초과하지 않는지 확인
- 업로드 중 오류 발생 시 파일을 나누어 재시도
- Instructions는 수정 가능하므로 점진적 개선 가능

## 🔧 문제 해결
- **파일 업로드 실패**: 파일 크기 확인, 네트워크 상태 점검
- **검색 결과 없음**: search_index.json이 제대로 로드되었는지 확인
- **느린 응답**: 질문을 더 구체적으로 수정

---
준비된 데이터로 강력한 건설 분야 AI 챗봇을 만들어보세요! 🏗️