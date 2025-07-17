@echo off
chcp 65001 > nul
title 한국 건설표준 GPT 완전 자동 설정

echo.
echo ████████████████████████████████████████████████████████████████
echo █                                                              █
echo █        🏗️ 한국 건설표준 GPT 완전 자동 설정 시스템 🏗️        █
echo █                                                              █
echo █   KDS/KCS/EXCS 5,233개 문서 → GPT API → ChatGPT 연동       █
echo █                                                              █
echo ████████████████████████████████████████████████████████████████
echo.

cd /d "%~dp0"

echo 📋 1단계: 환경 확인
echo ================================
echo.

REM Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다.
    echo    https://python.org 에서 Python 3.8+ 를 설치해주세요.
    echo.
    pause
    exit /b 1
)
echo ✅ Python 환경 확인됨

REM 필수 파일 확인
set "missing_files="
if not exist "search_index.json" set "missing_files=%missing_files% search_index.json"
if not exist "kcsc_structure.json" set "missing_files=%missing_files% kcsc_structure.json"
if not exist "lightweight_gpts_api_server.py" set "missing_files=%missing_files% lightweight_gpts_api_server.py"

if not "%missing_files%"=="" (
    echo ❌ 필수 파일이 누락되었습니다: %missing_files%
    echo    gpts_data 폴더에 모든 파일이 있는지 확인해주세요.
    echo.
    pause
    exit /b 1
)
echo ✅ 모든 필수 파일 확인됨

echo.
echo 📦 2단계: 패키지 설치
echo ================================
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 패키지 설치 실패
    echo.
    pause
    exit /b 1
)
echo ✅ 패키지 설치 완료

echo.
echo 🧪 3단계: 로컬 테스트
echo ================================
echo.

python test_api_local.py
if errorlevel 1 (
    echo ❌ 로컬 테스트 실패
    echo    문제를 해결한 후 다시 시도하세요.
    echo.
    pause
    exit /b 1
)
echo ✅ 로컬 테스트 통과

echo.
echo 🚀 4단계: Render 배포 안내
echo ================================
echo.

echo 이제 Render.com에 배포할 준비가 완료되었습니다!
echo.
echo 📋 Render 배포 단계:
echo    1. https://render.com 접속 및 계정 생성
echo    2. "New +" → "Web Service" 선택
echo    3. GitHub 저장소 연결 또는 파일 업로드
echo.
echo 🔧 서비스 설정:
echo    - Name: kcsc-gpt-api
echo    - Environment: Python 3
echo    - Build Command: pip install -r requirements.txt
echo    - Start Command: python lightweight_gpts_api_server.py
echo    - Plan: Free
echo.
echo 🔑 환경 변수:
echo    - API_KEY: kcsc-gpt-secure-key-2025
echo    - PORT: 10000
echo.

set /p continue="Render 배포를 진행하시겠습니까? (y/n): "
if /i not "%continue%"=="y" (
    echo 배포를 취소했습니다.
    pause
    exit /b 0
)

echo.
echo 🌐 5단계: 배포 진행
echo ================================
echo.

python auto_deploy_render.py
if errorlevel 1 (
    echo ❌ 배포 프로세스 실패
    echo.
    pause
    exit /b 1
)

echo.
echo 🤖 6단계: GPT 설정 안내
echo ================================
echo.

echo GPT 설정을 위해 다음 파일들을 확인하세요:
echo.
echo 📖 GPT_SETUP_COMPLETE_GUIDE.md - 완전한 설정 가이드
echo 📋 GPTs_INSTRUCTIONS.md - GPT Instructions 내용
echo 🔧 gpt_actions_schema.yaml - Actions 스키마
echo.

echo 🎯 ChatGPT에서 GPT 생성:
echo    1. https://chat.openai.com → "Explore" → "Create a GPT"
echo    2. GPTs_INSTRUCTIONS.md 내용을 Instructions에 복사
echo    3. Actions에서 API 연동 설정
echo    4. Knowledge 파일들 업로드
echo.

echo 🔑 API 정보:
echo    - API Key: kcsc-gpt-secure-key-2025
echo    - Base URL: [Render에서 제공된 URL]
echo.

echo.
echo 🎉 설정 완료!
echo ████████████████████████████████████████████████████████████████
echo █                                                              █
echo █                    🎊 축하합니다! 🎊                        █
echo █                                                              █
echo █     한국 건설표준 GPT 시스템이 성공적으로 구축되었습니다!     █
echo █                                                              █
echo █  이제 ChatGPT에서 전문적인 건설 표준 질문을 할 수 있습니다   █
echo █                                                              █
echo ████████████████████████████████████████████████████████████████
echo.

echo 📞 지원이 필요하시면:
echo    - README_DEPLOYMENT.md 파일 참조
echo    - Render 대시보드에서 로그 확인
echo    - API Health Check: [배포된 URL]/health
echo.

pause