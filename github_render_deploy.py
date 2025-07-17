#!/usr/bin/env python3
"""
GitHub 저장소 기반 Render 자동 배포 스크립트
커밋된 저장소를 Render에 연결하여 자동 배포합니다.
"""

import requests
import json
import time
import webbrowser
from datetime import datetime

class GitHubRenderDeployer:
    def __init__(self):
        self.github_repo = "https://github.com/Nicefree19/kcsc-gpt-api"
        self.render_service_name = "kcsc-gpt-api"
        self.api_key = "kcsc-gpt-secure-key-2025"
        
    def print_banner(self):
        print("🚀 GitHub → Render 자동 배포 시스템")
        print("=" * 50)
        print(f"📍 GitHub 저장소: {self.github_repo}")
        print(f"🏷️ 서비스명: {self.render_service_name}")
        print(f"🔑 API 키: {self.api_key}")
        print("=" * 50)
        
    def create_render_service_guide(self):
        """Render 서비스 생성 가이드"""
        print("\n🌐 Render 서비스 생성 단계별 가이드")
        print("=" * 40)
        
        steps = [
            "1. https://render.com 접속 및 로그인",
            "2. 'New +' 버튼 클릭",
            "3. 'Web Service' 선택",
            "4. 'Connect a repository' 선택",
            "5. GitHub 계정 연결 (처음인 경우)",
            f"6. '{self.github_repo.split('/')[-1]}' 저장소 선택",
            "7. 아래 설정값 입력"
        ]
        
        for step in steps:
            print(f"   {step}")
            
        print("\n📋 Render 서비스 설정값:")
        print("-" * 30)
        print(f"Name: {self.render_service_name}")
        print("Environment: Python 3")
        print("Region: Oregon (US West)")
        print("Branch: main")
        print("Build Command: pip install -r requirements.txt")
        print("Start Command: python lightweight_gpts_api_server.py")
        print("Plan: Free")
        print("Auto-Deploy: Yes")
        
        print("\n🔑 환경 변수 설정:")
        print("-" * 20)
        print(f"API_KEY = {self.api_key}")
        print("PORT = 10000")
        print("LOG_LEVEL = INFO")
        
    def open_render_dashboard(self):
        """Render 대시보드 열기"""
        render_url = "https://dashboard.render.com/web/new"
        print(f"\n🌐 Render 대시보드를 열고 있습니다...")
        print(f"URL: {render_url}")
        
        try:
            webbrowser.open(render_url)
            print("✅ 브라우저에서 Render 대시보드가 열렸습니다.")
        except:
            print("❌ 브라우저를 자동으로 열 수 없습니다.")
            print(f"수동으로 다음 URL을 열어주세요: {render_url}")
    
    def wait_for_deployment(self):
        """배포 완료 대기"""
        print("\n⏳ Render에서 배포를 완료해주세요...")
        print("배포 과정:")
        print("  1. 저장소 연결 및 설정")
        print("  2. 빌드 시작 (pip install)")
        print("  3. 서비스 시작")
        print("  4. URL 생성 완료")
        print("\n배포가 완료되면 아래에 URL을 입력해주세요.")
        
        while True:
            deployed_url = input("\n🌐 배포된 URL을 입력하세요 (예: https://kcsc-gpt-api.onrender.com): ").strip()
            
            if not deployed_url:
                continue
                
            if not deployed_url.startswith("http"):
                deployed_url = f"https://{deployed_url}"
                
            # URL 형식 검증
            if "onrender.com" in deployed_url:
                return deployed_url
            else:
                print("❌ Render URL 형식이 아닙니다. 다시 입력해주세요.")
    
    def test_deployment(self, base_url):
        """배포된 서비스 테스트"""
        print(f"\n🧪 배포 테스트 시작: {base_url}")
        print("-" * 40)
        
        tests = [
            ("Health Check", f"{base_url}/health", "GET", None),
            ("Root Endpoint", f"{base_url}/", "GET", None),
            ("OpenAPI Schema", f"{base_url}/openapi.json", "GET", None),
            ("Search API", f"{base_url}/api/v1/search", "POST", {
                "query": "콘크리트",
                "search_type": "keyword",
                "limit": 3
            })
        ]
        
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        passed = 0
        
        for test_name, url, method, data in tests:
            try:
                print(f"\n📋 {test_name} 테스트...")
                
                if method == "GET":
                    response = requests.get(url, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ 성공 (200)")
                    
                    # 응답 내용 간단히 표시
                    try:
                        json_data = response.json()
                        if test_name == "Health Check":
                            print(f"   상태: {json_data.get('status')}")
                            print(f"   문서 수: {json_data.get('documents_loaded')}")
                        elif test_name == "Search API":
                            results = json_data.get('data', {}).get('results', [])
                            print(f"   검색 결과: {len(results)}개")
                    except:
                        print(f"   응답 길이: {len(response.text)} bytes")
                    
                    passed += 1
                else:
                    print(f"❌ 실패 ({response.status_code})")
                    print(f"   오류: {response.text[:200]}")
                    
            except requests.RequestException as e:
                print(f"❌ 연결 오류: {e}")
            except Exception as e:
                print(f"❌ 테스트 오류: {e}")
        
        print(f"\n📊 테스트 결과: {passed}/{len(tests)} 통과")
        return passed == len(tests), base_url
    
    def generate_gpt_actions_config(self, api_url):
        """GPT Actions 설정 생성"""
        print(f"\n🤖 GPT Actions 설정 생성 중...")
        
        # 업데이트된 OpenAPI 스키마
        openapi_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "Korean Construction Standards API",
                "description": "한국 건설표준(KDS/KCS/EXCS) 검색 및 조회 API",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": api_url,
                    "description": "Production server"
                }
            ],
            "paths": {
                "/api/v1/search": {
                    "post": {
                        "operationId": "searchStandards",
                        "summary": "건설표준 검색",
                        "description": "코드, 키워드, 카테고리로 건설표준 검색",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["query"],
                                        "properties": {
                                            "query": {
                                                "type": "string",
                                                "description": "검색어 (표준코드, 키워드, 카테고리명)",
                                                "example": "KCS 14 20 01"
                                            },
                                            "search_type": {
                                                "type": "string",
                                                "enum": ["keyword", "code", "category"],
                                                "default": "keyword",
                                                "description": "검색 유형"
                                            },
                                            "limit": {
                                                "type": "integer",
                                                "minimum": 1,
                                                "maximum": 50,
                                                "default": 10,
                                                "description": "결과 개수 제한"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "검색 성공",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "data": {
                                                    "type": "object",
                                                    "properties": {
                                                        "results": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "code": {"type": "string"},
                                                                    "title": {"type": "string"},
                                                                    "content": {"type": "string"},
                                                                    "relevance_score": {"type": "number"},
                                                                    "metadata": {"type": "object"}
                                                                }
                                                            }
                                                        },
                                                        "total": {"type": "integer"}
                                                    }
                                                },
                                                "timestamp": {"type": "string", "format": "date-time"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/api/v1/standard/{code}": {
                    "get": {
                        "operationId": "getStandardDetail",
                        "summary": "표준 상세 조회",
                        "description": "특정 표준의 상세 내용 조회",
                        "parameters": [
                            {
                                "name": "code",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                                "description": "표준 코드",
                                "example": "KCS 14 20 01"
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "조회 성공",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "data": {
                                                    "type": "object",
                                                    "properties": {
                                                        "code": {"type": "string"},
                                                        "title": {"type": "string"},
                                                        "full_content": {"type": "string"},
                                                        "sections": {"type": "object"},
                                                        "metadata": {"type": "object"},
                                                        "related_standards": {
                                                            "type": "array",
                                                            "items": {"type": "string"}
                                                        }
                                                    }
                                                },
                                                "timestamp": {"type": "string", "format": "date-time"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                        "description": "API 키 인증"
                    }
                }
            },
            "security": [{"ApiKeyAuth": []}]
        }
        
        # 파일로 저장
        with open("gpt_actions_schema_updated.yaml", "w", encoding="utf-8") as f:
            import yaml
            yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True)
        
        print("✅ GPT Actions 스키마 업데이트 완료")
        print("📁 파일: gpt_actions_schema_updated.yaml")
        
        return openapi_schema
    
    def create_final_setup_guide(self, api_url):
        """최종 설정 가이드 생성"""
        guide_content = f"""
# 🎉 한국 건설표준 GPT 최종 설정 가이드

## ✅ 배포 완료 정보
- **API URL**: {api_url}
- **API Key**: {self.api_key}
- **GitHub 저장소**: {self.github_repo}
- **배포 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🤖 ChatGPT GPT 설정

### 1. 기본 정보
- **Name**: 한국 건설표준 AI 전문가
- **Description**: 한국 건설표준(KDS/KCS/EXCS) 5,233개 문서에 정통한 건설 분야 AI 전문가

### 2. Instructions
GPTs_INSTRUCTIONS.md 파일의 전체 내용을 복사하여 붙여넣기

### 3. Actions 설정
**방법 1: URL에서 가져오기 (권장)**
```
{api_url}/openapi.json
```

**방법 2: 스키마 직접 입력**
gpt_actions_schema_updated.yaml 파일 내용 복사

### 4. Authentication
- **Type**: API Key
- **API Key**: {self.api_key}
- **Auth Type**: Custom
- **Custom Header Name**: X-API-Key

### 5. Knowledge 파일 업로드 순서
1. search_index.json (필수)
2. kcsc_structure.json
3. kcsc_civil.json
4. kcsc_building.json
5. kcsc_facility.json
6. kcsc_excs.json
7. kcsc_high_quality_part1.json
8. kcsc_high_quality_part2.json
9. kcsc_high_quality_part3.json

### 6. Conversation Starters
- KCS 14 20 01의 내용을 알려줘
- 콘크리트 압축강도 시험 방법은?
- 지반조사 관련 표준을 알려줘
- 시공 순서도 생성해줘

## 🧪 테스트 방법

### API 직접 테스트
```bash
# Health Check
curl {api_url}/health

# 검색 테스트
curl -X POST {api_url}/api/v1/search \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: {self.api_key}" \\
  -d '{{"query": "콘크리트", "search_type": "keyword", "limit": 5}}'
```

### GPT 테스트 질문
```
"KCS 14 20 01에 대해 알려줘"
"콘크리트 압축강도 시험 방법을 설명해줘"
"지반조사 시 주의사항은?"
```

## 🔧 관리 및 모니터링

### Render 대시보드
- URL: https://dashboard.render.com
- 로그 확인, 재배포, 환경변수 수정 가능

### API 상태 확인
- Health Check: {api_url}/health
- 통계 정보: {api_url}/api/v1/stats

## 🎊 완성!
이제 한국 건설표준 5,233개 문서를 활용하는 전문 GPT가 준비되었습니다!
"""
        
        with open("FINAL_SETUP_GUIDE_COMPLETE.md", "w", encoding="utf-8") as f:
            f.write(guide_content)
        
        print("✅ 최종 설정 가이드 생성 완료")
        print("📁 파일: FINAL_SETUP_GUIDE_COMPLETE.md")
    
    def run(self):
        """전체 배포 프로세스 실행"""
        self.print_banner()
        
        # 1. Render 서비스 생성 가이드
        self.create_render_service_guide()
        
        # 2. Render 대시보드 열기
        input("\n⏳ Enter를 누르면 Render 대시보드를 엽니다...")
        self.open_render_dashboard()
        
        # 3. 배포 완료 대기
        deployed_url = self.wait_for_deployment()
        
        # 4. 배포 테스트
        success, api_url = self.test_deployment(deployed_url)
        
        if success:
            print("\n🎉 배포 테스트 성공!")
            
            # 5. GPT Actions 설정 생성
            self.generate_gpt_actions_config(api_url)
            
            # 6. 최종 설정 가이드 생성
            self.create_final_setup_guide(api_url)
            
            print("\n🏆 모든 설정이 완료되었습니다!")
            print("=" * 50)
            print(f"📍 API URL: {api_url}")
            print(f"🔑 API Key: {self.api_key}")
            print("📖 설정 가이드: FINAL_SETUP_GUIDE_COMPLETE.md")
            print("🤖 이제 ChatGPT에서 GPT를 설정하세요!")
            
        else:
            print("\n❌ 배포 테스트 실패")
            print("Render 대시보드에서 로그를 확인해주세요.")
        
        return success

if __name__ == "__main__":
    deployer = GitHubRenderDeployer()
    deployer.run()