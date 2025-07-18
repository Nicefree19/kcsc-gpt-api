#!/usr/bin/env python3
"""
Render 서버 배포 시 경로 문제 해결 스크립트
- 누락된 인덱스 파일 생성
- 경로 문제 자동 수정
"""

import os
import json
import shutil
from datetime import datetime

def create_missing_search_index():
    """누락된 search_index.json 생성"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # search_index.json이 없으면 생성
    search_index_path = os.path.join(current_dir, "search_index.json")
    
    if not os.path.exists(search_index_path):
        print("⚠️ search_index.json not found, creating from split_index.json...")
        
        # split_index.json에서 search_index.json 생성
        split_index_path = os.path.join(current_dir, "standards_split", "split_index.json")
        
        if os.path.exists(split_index_path):
            with open(split_index_path, 'r', encoding='utf-8') as f:
                split_data = json.load(f)
            
            # search_index 형식으로 변환
            search_index = {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "total_documents": len(split_data.get('standards', {})),
                "code_index": {}
            }
            
            for code, info in split_data.get('standards', {}).items():
                search_index["code_index"][code] = {
                    "title": info.get('title', ''),
                    "category": code.split()[0] if ' ' in code else code[:3],
                    "quality_score": 85,
                    "has_sections": {
                        "scope": info.get('has_parts', False),
                        "materials": info.get('has_parts', False),
                        "construction": info.get('has_parts', False),
                        "quality": info.get('has_parts', False),
                        "safety": info.get('has_parts', False)
                    },
                    "has_full": info.get('has_full', False),
                    "has_parts": info.get('has_parts', False),
                    "size_kb": info.get('size_kb', 0)
                }
            
            with open(search_index_path, 'w', encoding='utf-8') as f:
                json.dump(search_index, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Created search_index.json with {len(search_index['code_index'])} entries")
            return True
        else:
            print("❌ split_index.json also not found!")
            return False
    else:
        print("✅ search_index.json already exists")
        return True

def verify_file_structure():
    """파일 구조 검증"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    required_files = [
        "search_index.json",
        "standards_split/split_index.json",
        "enhanced_gpts_api_server.py",
        "lightweight_gpts_api_server.py",
        "requirements.txt"
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        full_path = os.path.join(current_dir, file_path)
        if os.path.exists(full_path):
            existing_files.append(file_path)
        else:
            missing_files.append(file_path)
    
    print("\n📁 File Structure Check:")
    print("✅ Existing files:")
    for file in existing_files:
        print(f"   - {file}")
    
    if missing_files:
        print("❌ Missing files:")
        for file in missing_files:
            print(f"   - {file}")
    
    return len(missing_files) == 0

def create_environment_config():
    """환경 설정 파일 생성"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # .env 파일 생성 (Render용)
    env_content = f"""# Render Environment Configuration
API_KEY=kcsc-gpt-secure-key-2025
LOG_LEVEL=INFO
INDEX_PATH=./search_index.json
SPLIT_DATA_PATH=./standards_split
PORT=10000
"""
    
    env_path = os.path.join(current_dir, ".env")
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ Created .env file for Render deployment")

def main():
    """메인 실행 함수"""
    print("🔧 Fixing Render deployment paths...")
    
    # 1. 누락된 search_index.json 생성
    create_missing_search_index()
    
    # 2. 파일 구조 검증
    all_files_exist = verify_file_structure()
    
    # 3. 환경 설정 생성
    create_environment_config()
    
    if all_files_exist:
        print("\n✅ All required files are present!")
        print("🚀 Ready for Render deployment")
    else:
        print("\n⚠️ Some files are missing, but deployment may still work")
    
    print("\n📋 Next steps:")
    print("1. Commit and push changes to GitHub")
    print("2. Redeploy on Render")
    print("3. Check logs for any remaining issues")

if __name__ == "__main__":
    main()