#!/usr/bin/env python3
"""
개선된 API 서버 로컬 테스트
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

class EnhancedAPITester:
    def __init__(self):
        self.base_url = "http://localhost:10000"
        self.api_key = "kcsc-gpt-secure-key-2025"
        self.headers = {"X-API-Key": self.api_key}
        
    def start_server(self):
        """로컬 서버 시작"""
        print("🚀 개선된 API 서버 시작 중...")
        try:
            self.server_process = subprocess.Popen([
                sys.executable, "enhanced_gpts_api_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            time.sleep(8)  # 더 긴 대기 시간
            print("✅ 서버 시작됨")
            return True
        except Exception as e:
            print(f"❌ 서버 시작 실패: {e}")
            return False
    
    def test_health_check(self):
        """헬스 체크 테스트"""
        print("\n🏥 헬스 체크 테스트...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=15)
            if response.status_code == 200:
                data = response.json()
                print("✅ 헬스 체크 성공")
                print(f"   상태: {data.get('status')}")
                print(f"   로드된 표준: {data.get('standards_loaded')}")
                print(f"   인덱스 표준: {data.get('split_index_loaded')}")
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
                "name": "콘크리트 키워드 검색",
                "data": {"query": "콘크리트", "search_type": "keyword", "limit": 3}
            },
            {
                "name": "KCS 14 20 01 코드 검색", 
                "data": {"query": "KCS 14 20 01", "search_type": "code", "limit": 1}
            },
            {
                "name": "구조 카테고리 검색",
                "data": {"query": "구조", "search_type": "category", "limit": 3}
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
                    timeout=20
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        results = data.get('data', {}).get('results', [])
                        print(f"  ✅ 성공: {len(results)}개 결과")
                        
                        if results:
                            first = results[0]
                            print(f"     - 코드: {first.get('code')}")
                            print(f"     - 제목: {first.get('title')[:50]}...")
                            print(f"     - 점수: {first.get('relevance_score')}")
                        
                        success_count += 1
                    else:
                        print(f"  ❌ API 오류: {data}")
                else:
                    print(f"  ❌ HTTP 오류: {response.status_code}")
                    print(f"     응답: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  ❌ 테스트 오류: {e}")
        
        print(f"\n📊 검색 테스트 결과: {success_count}/{len(test_cases)} 성공")
        return success_count == len(test_cases)
    
    def test_detail_api(self):
        """상세 조회 API 테스트"""
        print("\n📄 상세 조회 API 테스트...")
        
        test_codes = ["KCS 14 20 01", "KCS 14 20 10"]
        
        success_count = 0
        for code in test_codes:
            try:
                print(f"  테스트 코드: {code}")
                
                detail_response = requests.get(
                    f"{self.base_url}/api/v1/standard/{code}",
                    headers=self.headers,
                    timeout=15
                )
                
                if detail_response.status_code == 200:
                    data = detail_response.json()
                    if data.get('success'):
                        detail_data = data.get('data', {})
                        print("  ✅ 상세 조회 성공")
                        print(f"     - 코드: {detail_data.get('code')}")
                        print(f"     - 제목: {detail_data.get('title')[:50]}...")
                        print(f"     - 내용 길이: {len(str(detail_data.get('content', '')))}")
                        success_count += 1
                    else:
                        print(f"  ❌ API 오류: {data}")
                else:
                    print(f"  ❌ HTTP 오류: {detail_response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ 상세 조회 오류: {e}")
        
        print(f"\n📊 상세 조회 결과: {success_count}/{len(test_codes)} 성공")
        return success_count > 0
    
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
                if data.get('success'):
                    stats = data.get('data', {})
                    print("✅ 통계 조회 성공")
                    print(f"   총 표준: {stats.get('total_standards')}")
                    print(f"   인덱스 표준: {stats.get('total_in_index')}")
                    print(f"   카테고리 수: {stats.get('total_categories')}")
                    print(f"   서버 유형: {stats.get('server_type')}")
                    return True
                else:
                    print(f"❌ API 오류: {data}")
            else:
                print(f"❌ 통계 조회 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 통계 조회 오류: {e}")
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
        print("🧪 개선된 한국 건설표준 API 테스트 시작")
        print("=" * 60)
        
        if not self.start_server():
            return False
        
        try:
            tests = [
                ("헬스 체크", self.test_health_check),
                ("검색 API", self.test_search_api),
                ("상세 조회 API", self.test_detail_api),
                ("통계 API", self.test_stats_api)
            ]
            
            passed = 0
            total = len(tests)
            
            for test_name, test_func in tests:
                if test_func():
                    passed += 1
            
            print(f"\n🎉 테스트 완료: {passed}/{total} 통과")
            
            if passed >= 3:  # 4개 중 3개 이상 통과하면 성공
                print("✅ 대부분 테스트 통과! Render 배포 준비 완료")
                print("\n📋 다음 단계:")
                print("1. GitHub에 enhanced_gpts_api_server.py 커밋")
                print("2. Render에서 자동 배포 확인")
                print("3. ChatGPT Actions에서 API 연결 테스트")
                return True
            else:
                print("❌ 일부 테스트 실패. 문제를 해결한 후 다시 시도하세요.")
                return False
                
        finally:
            self.stop_server()

if __name__ == "__main__":
    tester = EnhancedAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)