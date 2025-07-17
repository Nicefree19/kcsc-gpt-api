#!/usr/bin/env python3
"""
로컬 API 서버 테스트 스크립트
배포 전 로컬에서 API 기능을 테스트합니다.
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

class LocalAPITester:
    def __init__(self):
        self.base_url = "http://localhost:10000"
        self.api_key = "kcsc-gpt-secure-key-2025"
        self.headers = {"X-API-Key": self.api_key}
        
    def start_server(self):
        """로컬 서버 시작"""
        print("🚀 로컬 API 서버 시작 중...")
        try:
            # 백그라운드에서 서버 시작
            self.server_process = subprocess.Popen([
                sys.executable, "lightweight_gpts_api_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 서버 시작 대기
            time.sleep(5)
            print("✅ 서버 시작됨")
            return True
        except Exception as e:
            print(f"❌ 서버 시작 실패: {e}")
            return False
    
    def test_health_check(self):
        """헬스 체크 테스트"""
        print("\n🏥 헬스 체크 테스트...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("✅ 헬스 체크 성공")
                print(f"   상태: {data.get('status')}")
                print(f"   로드된 문서: {data.get('documents_loaded')}")
                return True
            else:
                print(f"❌ 헬스 체크 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 헬스 체크 오류: {e}")
            return False
    
    def test_search_api(self):
        """검색 API 테스트"""
        print("\n🔍 검색 API 테스트...")
        
        test_cases = [
            {
                "name": "키워드 검색",
                "data": {"query": "콘크리트", "search_type": "keyword", "limit": 3}
            },
            {
                "name": "코드 검색", 
                "data": {"query": "KCS 14 20 01", "search_type": "code", "limit": 1}
            },
            {
                "name": "카테고리 검색",
                "data": {"query": "지반", "search_type": "category", "limit": 3}
            }
        ]
        
        success_count = 0
        for test_case in test_cases:
            try:
                print(f"\n  📋 {test_case['name']} 테스트...")
                response = requests.post(
                    f"{self.base_url}/api/v1/search",
                    json=test_case['data'],
                    headers=self.headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('data', {}).get('results', [])
                    print(f"  ✅ 성공: {len(results)}개 결과")
                    
                    # 첫 번째 결과 출력
                    if results:
                        first = results[0]
                        print(f"     - 코드: {first.get('code')}")
                        print(f"     - 제목: {first.get('title')[:50]}...")
                        print(f"     - 점수: {first.get('relevance_score')}")
                    
                    success_count += 1
                else:
                    print(f"  ❌ 실패: {response.status_code}")
                    print(f"     응답: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  ❌ 오류: {e}")
        
        print(f"\n📊 검색 테스트 결과: {success_count}/{len(test_cases)} 성공")
        return success_count == len(test_cases)
    
    def test_detail_api(self):
        """상세 조회 API 테스트"""
        print("\n📄 상세 조회 API 테스트...")
        
        # 먼저 검색으로 유효한 코드 찾기
        try:
            search_response = requests.post(
                f"{self.base_url}/api/v1/search",
                json={"query": "콘크리트", "search_type": "keyword", "limit": 1},
                headers=self.headers,
                timeout=10
            )
            
            if search_response.status_code == 200:
                results = search_response.json().get('data', {}).get('results', [])
                if results:
                    test_code = results[0]['code']
                    print(f"  테스트 코드: {test_code}")
                    
                    # 상세 조회 테스트
                    detail_response = requests.get(
                        f"{self.base_url}/api/v1/standard/{test_code}",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if detail_response.status_code == 200:
                        data = detail_response.json()
                        detail_data = data.get('data', {})
                        print("  ✅ 상세 조회 성공")
                        print(f"     - 코드: {detail_data.get('code')}")
                        print(f"     - 제목: {detail_data.get('title')}")
                        print(f"     - 내용 길이: {len(detail_data.get('full_content', ''))}")
                        return True
                    else:
                        print(f"  ❌ 상세 조회 실패: {detail_response.status_code}")
                        return False
                else:
                    print("  ❌ 테스트할 코드를 찾을 수 없음")
                    return False
            else:
                print(f"  ❌ 검색 실패: {search_response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ 상세 조회 오류: {e}")
            return False
    
    def test_keywords_api(self):
        """키워드 API 테스트"""
        print("\n🏷️ 키워드 API 테스트...")
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/keywords?limit=10",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                keywords = data.get('data', {}).get('keywords', [])
                print(f"✅ 키워드 조회 성공: {len(keywords)}개")
                print(f"   상위 키워드: {', '.join(keywords[:5])}")
                return True
            else:
                print(f"❌ 키워드 조회 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 키워드 조회 오류: {e}")
            return False
    
    def test_stats_api(self):
        """통계 API 테스트"""
        print("\n📊 통계 API 테스트...")
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/stats",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('data', {})
                print("✅ 통계 조회 성공")
                print(f"   총 문서: {stats.get('total_documents')}")
                print(f"   총 카테고리: {stats.get('total_categories')}")
                print(f"   총 키워드: {stats.get('total_keywords')}")
                print(f"   서버 유형: {stats.get('server_type')}")
                return True
            else:
                print(f"❌ 통계 조회 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 통계 조회 오류: {e}")
            return False
    
    def test_openapi_schema(self):
        """OpenAPI 스키마 테스트"""
        print("\n📋 OpenAPI 스키마 테스트...")
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            
            if response.status_code == 200:
                schema = response.json()
                print("✅ OpenAPI 스키마 조회 성공")
                print(f"   제목: {schema.get('info', {}).get('title')}")
                print(f"   버전: {schema.get('info', {}).get('version')}")
                print(f"   경로 수: {len(schema.get('paths', {}))}")
                return True
            else:
                print(f"❌ OpenAPI 스키마 조회 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ OpenAPI 스키마 조회 오류: {e}")
            return False
    
    def stop_server(self):
        """서버 중지"""
        if hasattr(self, 'server_process'):
            print("\n🛑 서버 중지 중...")
            self.server_process.terminate()
            self.server_process.wait()
            print("✅ 서버 중지됨")
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🧪 한국 건설표준 API 로컬 테스트 시작")
        print("=" * 50)
        
        # 서버 시작
        if not self.start_server():
            return False
        
        try:
            tests = [
                ("헬스 체크", self.test_health_check),
                ("검색 API", self.test_search_api),
                ("상세 조회 API", self.test_detail_api),
                ("키워드 API", self.test_keywords_api),
                ("통계 API", self.test_stats_api),
                ("OpenAPI 스키마", self.test_openapi_schema)
            ]
            
            passed = 0
            total = len(tests)
            
            for test_name, test_func in tests:
                if test_func():
                    passed += 1
            
            print(f"\n🎉 테스트 완료: {passed}/{total} 통과")
            
            if passed == total:
                print("✅ 모든 테스트 통과! Render 배포 준비 완료")
                return True
            else:
                print("❌ 일부 테스트 실패. 문제를 해결한 후 다시 시도하세요.")
                return False
                
        finally:
            self.stop_server()

if __name__ == "__main__":
    tester = LocalAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)