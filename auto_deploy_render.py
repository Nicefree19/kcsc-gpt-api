#!/usr/bin/env python3
"""
Render.com 자동 배포 스크립트
한국 건설표준 GPT API 서버를 Render에 자동으로 배포합니다.
"""

import os
import json
import subprocess
import sys
from pathlib import Path
import shutil
import requests
import time

class RenderDeployer:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.api_key = "kcsc-gpt-secure-key-2025"
        
    def check_requirements(self):
        """필수 요구사항 확인"""
        print("🔍 필수 요구사항 확인 중...")
        
        # Git 확인
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            print("✅ Git 설치됨")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Git이 설치되지 않았습니다. Git을 먼저 설치해주세요.")
            return False
            
        # 필수 파일 확인
        required_files = [
            "render.yaml",
            "requirements.txt", 
            "lightweight_gpts_api_server.py",
            "search_index.json"
        ]
        
        for file in required_files:
            if not (self.project_dir / file).exists():
                print(f"❌ 필수 파일 누락: {file}")
                return False
            print(f"✅ {file} 확인됨")
            
        return True
    
    def setup_git_repo(self):
        """Git 저장소 설정"""
        print("\n📁 Git 저장소 설정 중...")
        
        os.chdir(self.project_dir)
        
        # Git 초기화
        if not (self.project_dir / ".git").exists():
            subprocess.run(["git", "init"], check=True)
            print("✅ Git 저장소 초기화됨")
        
        # .gitignore 생성
        gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Local env
.env
.env.local
.env.*.local
"""
        
        with open(".gitignore", "w", encoding="utf-8") as f:
            f.write(gitignore_content.strip())
        
        # 파일 추가 및 커밋
        subprocess.run(["git", "add", "."], check=True)
        
        try:
            subprocess.run([
                "git", "commit", "-m", "Initial commit: Korean Construction Standards GPT API"
            ], check=True)
            print("✅ 초기 커밋 완료")
        except subprocess.CalledProcessError:
            print("ℹ️ 커밋할 변경사항이 없습니다.")
    
    def create_render_service(self):
        """Render 서비스 생성 안내"""
        print("\n🚀 Render 서비스 생성 안내")
        print("=" * 50)
        print("1. https://render.com 에 접속하여 계정을 생성하세요.")
        print("2. 'New +' 버튼을 클릭하고 'Web Service'를 선택하세요.")
        print("3. GitHub 저장소를 연결하거나 다음 설정을 사용하세요:")
        print()
        print("📋 Render 서비스 설정:")
        print(f"   - Name: kcsc-gpt-api")
        print(f"   - Environment: Python 3")
        print(f"   - Build Command: pip install -r requirements.txt")
        print(f"   - Start Command: python lightweight_gpts_api_server.py")
        print(f"   - Plan: Free")
        print()
        print("🔑 환경 변수 설정:")
        print(f"   - API_KEY: {self.api_key}")
        print(f"   - PORT: 10000")
        print()
        print("4. 배포가 완료되면 제공된 URL을 확인하세요.")
        print("   예: https://kcsc-gpt-api.onrender.com")
        
    def test_deployment(self, base_url):
        """배포 테스트"""
        print(f"\n🧪 배포 테스트 중... ({base_url})")
        
        try:
            # Health check
            response = requests.get(f"{base_url}/health", timeout=30)
            if response.status_code == 200:
                print("✅ Health check 성공")
                data = response.json()
                print(f"   - 상태: {data.get('status')}")
                print(f"   - 로드된 문서: {data.get('documents_loaded')}")
            else:
                print(f"❌ Health check 실패: {response.status_code}")
                return False
                
            # API 테스트
            headers = {"X-API-Key": self.api_key}
            test_data = {
                "query": "콘크리트",
                "search_type": "keyword",
                "limit": 5
            }
            
            response = requests.post(
                f"{base_url}/api/v1/search",
                json=test_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ API 검색 테스트 성공")
                data = response.json()
                results = data.get('data', {}).get('results', [])
                print(f"   - 검색 결과: {len(results)}개")
            else:
                print(f"❌ API 테스트 실패: {response.status_code}")
                return False
                
            return True
            
        except requests.RequestException as e:
            print(f"❌ 연결 오류: {e}")
            return False
    
    def generate_gpt_setup_guide(self):
        """GPT 설정 가이드 생성"""
        print("\n📝 GPT 설정 가이드 생성 중...")
        
        guide_content = f"""
# 한국 건설표준 GPT 설정 가이드

## 🎯 GPT 생성 단계

### 1. ChatGPT Plus 계정으로 로그인
- https://chat.openai.com 접속
- GPTs 메뉴에서 "Create a GPT" 선택

### 2. 기본 정보 설정
**Name:** 한국 건설표준 AI 전문가

**Description:** 
한국 건설표준(KDS/KCS/EXCS) 5,233개 문서에 정통한 건설 분야 AI 전문가입니다. 표준 검색, 기술 자문, 참조 제공, 실무 가이드를 제공합니다.

### 3. Instructions 설정
다음 내용을 Instructions에 복사하세요:

```
{open('GPTs_INSTRUCTIONS.md', 'r', encoding='utf-8').read()}
```

### 4. Capabilities 설정
- ✅ Web Browsing
- ✅ Code Interpreter  
- ❌ DALL·E Image Generation

### 5. Actions 설정
**Import from URL:** 
```
https://kcsc-gpt-api.onrender.com/openapi.json
```

**Authentication:**
- Type: API Key
- API Key: {self.api_key}
- Auth Type: Custom
- Custom Header Name: X-API-Key

### 6. Knowledge 파일 업로드 (순서대로)
1. search_index.json (필수)
2. kcsc_structure.json
3. kcsc_civil.json
4. kcsc_building.json
5. kcsc_facility.json
6. kcsc_excs.json
7. kcsc_high_quality_part1.json
8. kcsc_high_quality_part2.json
9. kcsc_high_quality_part3.json

**주의:** 총 용량이 512MB를 초과하지 않도록 조절하세요.

### 7. Conversation Starters 설정
- KCS 14 20 01의 내용을 알려줘
- 콘크리트 압축강도 시험 방법은?
- 지반조사 관련 표준을 알려줘
- 시공 순서도 생성해줘

### 8. 테스트 및 배포
1. "Test" 버튼으로 기능 테스트
2. "Save" 버튼으로 저장
3. "Publish" 버튼으로 배포 (Public/Anyone with link 선택)

## 🔧 API 서버 정보
- **Base URL:** https://kcsc-gpt-api.onrender.com
- **API Key:** {self.api_key}
- **Health Check:** https://kcsc-gpt-api.onrender.com/health

## 📊 사용 통계 확인
GPT 사용 후 다음 URL에서 통계를 확인할 수 있습니다:
https://kcsc-gpt-api.onrender.com/api/v1/stats?X-API-Key={self.api_key}

## 🆘 문제 해결
1. **API 연결 실패:** Render 서비스가 활성화되어 있는지 확인
2. **검색 결과 없음:** API 키가 올바른지 확인
3. **응답 속도 느림:** 무료 플랜의 콜드 스타트 현상 (첫 요청 시 지연)

## 📞 지원
문제가 발생하면 다음을 확인하세요:
- Render 대시보드에서 로그 확인
- API Health Check 상태 확인
- GPT Actions 설정 재확인
"""
        
        with open("GPT_SETUP_COMPLETE_GUIDE.md", "w", encoding="utf-8") as f:
            f.write(guide_content)
        
        print("✅ GPT 설정 가이드 생성 완료: GPT_SETUP_COMPLETE_GUIDE.md")
    
    def run(self):
        """전체 배포 프로세스 실행"""
        print("🚀 한국 건설표준 GPT API 자동 배포 시작")
        print("=" * 60)
        
        # 1. 요구사항 확인
        if not self.check_requirements():
            print("\n❌ 배포 중단: 필수 요구사항을 충족하지 않습니다.")
            return False
        
        # 2. Git 저장소 설정
        self.setup_git_repo()
        
        # 3. Render 서비스 생성 안내
        self.create_render_service()
        
        # 4. 사용자 입력 대기
        print("\n⏳ Render에서 배포를 완료한 후 계속하려면 Enter를 누르세요...")
        input()
        
        # 5. 배포 URL 입력 받기
        while True:
            base_url = input("🌐 배포된 URL을 입력하세요 (예: https://kcsc-gpt-api.onrender.com): ").strip()
            if base_url.startswith("http"):
                break
            print("❌ 올바른 URL을 입력해주세요.")
        
        # 6. 배포 테스트
        if self.test_deployment(base_url):
            print("\n✅ 배포 테스트 성공!")
        else:
            print("\n❌ 배포 테스트 실패. Render 로그를 확인해주세요.")
        
        # 7. GPT 설정 가이드 생성
        self.generate_gpt_setup_guide()
        
        print("\n🎉 배포 완료!")
        print("=" * 60)
        print(f"📍 API URL: {base_url}")
        print(f"🔑 API Key: {self.api_key}")
        print("📖 GPT 설정: GPT_SETUP_COMPLETE_GUIDE.md 파일을 참조하세요.")
        
        return True

if __name__ == "__main__":
    deployer = RenderDeployer()
    success = deployer.run()
    sys.exit(0 if success else 1)