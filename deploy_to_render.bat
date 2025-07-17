@echo off
chcp 65001 > nul
echo.
echo 🚀 한국 건설표준 GPT API - Render 자동 배포
echo ================================================
echo.

cd /d "%~dp0"

echo 📋 필수 파일 확인 중...
if not exist "search_index.json" (
    echo ❌ search_index.json 파일이 없습니다.
    pause
    exit /b 1
)

if not exist "kcsc_structure.json" (
    echo ❌ kcsc_structure.json 파일이 없습니다.
    pause
    exit /b 1
)

if not exist "lightweight_gpts_api_server.py" (
    echo ❌ lightweight_gpts_api_server.py 파일이 없습니다.
    pause
    exit /b 1
)

echo ✅ 모든 필수 파일이 준비되었습니다.
echo.

echo 🔧 Python 환경 확인 중...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다.
    echo    https://python.org 에서 Python을 설치해주세요.
    pause
    exit /b 1
)

echo ✅ Python 환경 확인됨
echo.

echo 📦 필요한 패키지 설치 중...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 패키지 설치 실패
    pause
    exit /b 1
)

echo ✅ 패키지 설치 완료
echo.

echo 🧪 로컬 테스트 실행 중...
echo    서버가 시작되면 Ctrl+C로 중단하고 다음 단계로 진행하세요.
echo.
timeout /t 3 > nul

start /b python lightweight_gpts_api_server.py
timeout /t 5 > nul

echo.
echo 🌐 Render.com 배포 안내
echo ========================
echo.
echo 1. https://render.com 에 접속하여 계정을 생성하세요.
echo 2. 'New +' 버튼 클릭 → 'Web Service' 선택
echo 3. GitHub 저장소 연결 또는 다음 설정 사용:
echo.
echo    📋 서비스 설정:
echo    - Name: kcsc-gpt-api
echo    - Environment: Python 3
echo    - Build Command: pip install -r requirements.txt
echo    - Start Command: python lightweight_gpts_api_server.py
echo    - Plan: Free
echo.
echo    🔑 환경 변수:
echo    - API_KEY: kcsc-gpt-secure-key-2025
echo    - PORT: 10000
echo.
echo 4. 배포 완료 후 제공된 URL 확인
echo    예: https://kcsc-gpt-api.onrender.com
echo.

pause

echo.
echo 📖 GPT 설정 가이드가 생성되었습니다.
echo    GPT_SETUP_COMPLETE_GUIDE.md 파일을 확인하세요.
echo.

python auto_deploy_render.py

echo.
echo 🎉 배포 프로세스 완료!
echo.
echo 📍 다음 단계:
echo    1. Render에서 배포 상태 확인
echo    2. GPT_SETUP_COMPLETE_GUIDE.md 파일 참조하여 GPT 설정
echo    3. ChatGPT에서 새 GPT 생성 및 테스트
echo.

pause