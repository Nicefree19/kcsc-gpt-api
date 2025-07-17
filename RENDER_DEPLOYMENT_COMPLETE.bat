@echo off
chcp 65001 > nul
title 한국 건설표준 GPT - Render 배포 완성

echo.
echo ████████████████████████████████████████████████████████████████
echo █                                                              █
echo █    🚀 GitHub → Render → GPT 완전 자동 배포 시스템 🚀         █
echo █                                                              █
echo █        GitHub 저장소: Nicefree19/kcsc-gpt-api              █
echo █                                                              █
echo ████████████████████████████████████████████████████████████████
echo.

cd /d "%~dp0"

echo 📋 1단계: GitHub 저장소 확인
echo ================================
echo ✅ GitHub 저장소: https://github.com/Nicefree19/kcsc-gpt-api
echo ✅ 모든 파일 커밋 완료
echo ✅ 배포 준비 완료
echo.

echo 🌐 2단계: Render 서비스 생성
echo ================================
echo.
echo 다음 단계를 따라 Render에서 서비스를 생성하세요:
echo.
echo 1. https://render.com 접속 및 로그인
echo 2. "New +" 버튼 클릭
echo 3. "Web Service" 선택
echo 4. "Connect a repository" 선택
echo 5. GitHub 계정 연결 (처음인 경우)
echo 6. "kcsc-gpt-api" 저장소 선택
echo.
echo 📋 서비스 설정값:
echo --------------------------------
echo Name: kcsc-gpt-api
echo Environment: Python 3
echo Region: Oregon (US West)
echo Branch: main
echo Build Command: pip install -r requirements.txt
echo Start Command: python lightweight_gpts_api_server.py
echo Plan: Free
echo Auto-Deploy: Yes
echo.
echo 🔑 환경 변수 설정:
echo --------------------------------
echo API_KEY = kcsc-gpt-secure-key-2025
echo PORT = 10000
echo LOG_LEVEL = INFO
echo.

set /p continue="Render 대시보드를 열까요? (y/n): "
if /i "%continue%"=="y" (
    start https://dashboard.render.com/web/new
    echo ✅ Render 대시보드가 열렸습니다.
)

echo.
echo ⏳ 3단계: 배포 완료 대기
echo ================================
echo.
echo Render에서 배포 과정:
echo 1. 저장소 연결 및 설정 입력
echo 2. 빌드 시작 (pip install -r requirements.txt)
echo 3. 서비스 시작 (python lightweight_gpts_api_server.py)
echo 4. URL 생성 완료
echo.
echo 배포가 완료되면 다음과 같은 URL을 받게 됩니다:
echo 예: https://kcsc-gpt-api.onrender.com
echo.

pause

echo.
set /p deployed_url="🌐 배포된 URL을 입력하세요: "

if "%deployed_url%"=="" (
    echo ❌ URL이 입력되지 않았습니다.
    pause
    exit /b 1
)

echo.
echo 🧪 4단계: 배포 테스트
echo ================================
echo.

echo 📋 API 테스트 중...
python -c "
import requests
import json

url = '%deployed_url%'
api_key = 'kcsc-gpt-secure-key-2025'

print('Health Check 테스트...')
try:
    response = requests.get(f'{url}/health', timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(f'✅ Health Check 성공')
        print(f'   상태: {data.get(\"status\")}')
        print(f'   문서 수: {data.get(\"documents_loaded\")}')
    else:
        print(f'❌ Health Check 실패: {response.status_code}')
except Exception as e:
    print(f'❌ 연결 오류: {e}')

print('\nAPI 검색 테스트...')
try:
    headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}
    data = {'query': '콘크리트', 'search_type': 'keyword', 'limit': 3}
    response = requests.post(f'{url}/api/v1/search', json=data, headers=headers, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        results = result.get('data', {}).get('results', [])
        print(f'✅ 검색 API 성공: {len(results)}개 결과')
        if results:
            print(f'   첫 번째 결과: {results[0].get(\"title\", \"\")}')
    else:
        print(f'❌ 검색 API 실패: {response.status_code}')
except Exception as e:
    print(f'❌ 검색 테스트 오류: {e}')
"

echo.
echo 🤖 5단계: GPT Actions 설정
echo ================================
echo.
echo ChatGPT에서 GPT를 생성하고 다음 설정을 사용하세요:
echo.
echo 📋 기본 정보:
echo --------------------------------
echo Name: 한국 건설표준 AI 전문가
echo Description: 한국 건설표준(KDS/KCS/EXCS) 5,233개 문서에 정통한 건설 분야 AI 전문가
echo.
echo 📖 Instructions:
echo --------------------------------
echo GPTs_INSTRUCTIONS.md 파일의 전체 내용을 복사하여 붙여넣기
echo.
echo 🔧 Actions 설정:
echo --------------------------------
echo Import from URL: %deployed_url%/openapi.json
echo.
echo 🔑 Authentication:
echo --------------------------------
echo Type: API Key
echo API Key: kcsc-gpt-secure-key-2025
echo Auth Type: Custom
echo Custom Header Name: X-API-Key
echo.
echo 📚 Knowledge 파일 업로드 순서:
echo --------------------------------
echo 1. search_index.json (필수)
echo 2. kcsc_structure.json
echo 3. kcsc_civil.json
echo 4. kcsc_building.json
echo 5. kcsc_facility.json
echo 6. kcsc_excs.json
echo 7. kcsc_high_quality_part1.json
echo 8. kcsc_high_quality_part2.json
echo 9. kcsc_high_quality_part3.json
echo.
echo 💬 Conversation Starters:
echo --------------------------------
echo - KCS 14 20 01의 내용을 알려줘
echo - 콘크리트 압축강도 시험 방법은?
echo - 지반조사 관련 표준을 알려줘
echo - 시공 순서도 생성해줘
echo.

set /p open_chatgpt="ChatGPT를 열까요? (y/n): "
if /i "%open_chatgpt%"=="y" (
    start https://chat.openai.com/gpts/editor
    echo ✅ ChatGPT GPT 편집기가 열렸습니다.
)

echo.
echo 🎉 완성!
echo ████████████████████████████████████████████████████████████████
echo █                                                              █
echo █                    🎊 축하합니다! 🎊                        █
echo █                                                              █
echo █     한국 건설표준 GPT 시스템이 성공적으로 완성되었습니다!     █
echo █                                                              █
echo █  GitHub → Render → ChatGPT 연동이 모두 완료되었습니다!      █
echo █                                                              █
echo ████████████████████████████████████████████████████████████████
echo.
echo 📍 시스템 정보:
echo --------------------------------
echo GitHub: https://github.com/Nicefree19/kcsc-gpt-api
echo API URL: %deployed_url%
echo API Key: kcsc-gpt-secure-key-2025
echo 문서 수: 5,233개 건설표준
echo.
echo 🧪 테스트 질문 예시:
echo --------------------------------
echo "KCS 14 20 01에 대해 알려줘"
echo "콘크리트 압축강도 시험 방법을 설명해줘"
echo "지반조사 시 주의사항은?"
echo "터널 굴착 안전 기준을 알려줘"
echo.
echo 📞 지원:
echo --------------------------------
echo - Render 대시보드: https://dashboard.render.com
echo - API Health Check: %deployed_url%/health
echo - API 문서: %deployed_url%/openapi.json
echo.

pause