# GitHub Push 가이드

## 커밋 완료

GPTs 데이터 코드 정규화 및 search_index 동기화 작업이 성공적으로 커밋되었습니다.

### 커밋 정보
- **커밋 해시**: 70bb5a4
- **변경 파일**: 23개
- **주요 변경사항**:
  - 모든 GPTs 데이터 파일의 코드 형식 표준화
  - search_index.json 동기화 (1.2MB - 대용량 아님)
  - API 서버 코드 정규화 기능 추가
  - Render 배포 관련 파일들 추가

## GitHub Push 방법

WSL2 환경에서 인증 문제로 직접 push가 안 되므로, Windows에서 수행하세요:

### 1. Windows PowerShell 또는 Command Prompt에서:
```bash
cd D:\00.Work_AI_Tool\06.GPTs_kcsc
git push origin master
```

### 2. 또는 GitHub Desktop 사용:
- GitHub Desktop 실행
- 해당 저장소 선택
- Push origin 버튼 클릭

### 3. 개인 액세스 토큰 사용 (필요시):
```bash
git push https://YOUR_TOKEN@github.com/Nicefree19/kcsc-gpt-api.git master
```

## 제외된 대용량 파일

`.gitignore`에 의해 다음 파일들은 제외되었습니다:
- kcsc_high_quality.json (337MB)
- kcsc_high_quality_part*.json (100MB+)
- kcsc_building.json (62MB)
- kcsc_civil.json (51MB)
- kcsc_excs.json (38MB)
- kcsc_facility.json (34MB)
- kcsc_structure.json (23MB)
- standards_split/ 폴더 전체

## 포함된 중요 파일

✅ **search_index.json** (1.2MB) - API 서버의 핵심 인덱스
✅ **enhanced_gpts_api_server.py** - 개선된 API 서버 코드
✅ **lightweight_gpts_api_server.py** - 경량 API 서버
✅ **FINAL_GPT_ACTIONS_SCHEMA.json** - GPT Actions 스키마
✅ 모든 문서 파일 (.md)
✅ 배포 관련 스크립트

## Render 서버 자동 배포

GitHub에 push가 완료되면 Render 서버가 자동으로:
1. 새 코드를 감지
2. Docker 이미지 빌드
3. 서버 재배포

약 5-10분 후 변경사항이 반영됩니다.

## 확인 사항

push 후 다음을 확인하세요:
- https://kcsc-gpt-api.onrender.com/health
- https://kcsc-gpt-api.onrender.com/api/v1/search (API 키 필요)

코드 정규화 테스트:
- `KDS_14_20_01` 검색
- `KDS-14-20-01` 검색
- `EXCS_10_10_05` 검색

모두 정상적으로 작동해야 합니다.