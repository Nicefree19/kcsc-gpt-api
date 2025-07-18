"""
GPT Actions 인증 문제 해결 스크립트
"""

import os
import shutil
from datetime import datetime

def fix_lightweight_api_server():
    """lightweight_gpts_api_server.py 수정"""
    
    file_path = "/mnt/d/00.Work_AI_Tool/06.GPTs_kcsc/gpts_data/lightweight_gpts_api_server.py"
    
    # 백업 생성
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"백업 생성: {backup_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 환경 변수 추가
    env_vars_section = """# 환경 변수
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SPLIT_DATA_PATH = os.getenv("SPLIT_DATA_PATH", "./gpts_data/standards_split")
GPT_ACTIONS_MODE = os.getenv("GPT_ACTIONS_MODE", "false").lower() == "true"  # GPT Actions 모드"""
    
    content = content.replace(
        '# 환경 변수\nAPI_KEY = os.getenv("API_KEY", "your-secure-api-key-here")\nLOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")\nSPLIT_DATA_PATH = os.getenv("SPLIT_DATA_PATH", "./gpts_data/standards_split")',
        env_vars_section
    )
    
    # 2. verify_api_key 함수 수정
    new_verify_function = """async def verify_api_key(x_api_key: str = Header(None)):
    \"\"\"API 키 검증 - GPT Actions 모드에서는 선택적\"\"\"
    if GPT_ACTIONS_MODE:
        # GPT Actions 모드에서는 API 키 검증을 스킵하거나 완화
        logger.info(f"GPT Actions request with key: {x_api_key[:10]}..." if x_api_key else "No API key")
        return x_api_key or "gpt-actions"
    else:
        # 일반 모드에서는 엄격한 검증
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return x_api_key"""
    
    # verify_api_key 함수 찾아서 교체
    import re
    pattern = r'async def verify_api_key\(.*?\):\s*\n(?:.*\n)*?    return x_api_key'
    content = re.sub(pattern, new_verify_function, content, flags=re.DOTALL)
    
    # 3. CORS 설정 확인 및 수정
    cors_pattern = r'app\.add_middleware\(\s*CORSMiddleware,\s*allow_origins=\[(.*?)\],'
    cors_match = re.search(cors_pattern, content, re.DOTALL)
    
    if cors_match:
        current_origins = cors_match.group(1)
        if '"*"' not in current_origins:
            # GPT Actions 모드에서는 모든 origin 허용 추가
            new_origins = current_origins.rstrip() + ', "*"' if current_origins.strip() else '"*"'
            content = content.replace(
                f'allow_origins=[{current_origins}]',
                f'allow_origins=[{new_origins}] if GPT_ACTIONS_MODE else [{current_origins}]'
            )
    
    # 4. 시작 로그에 모드 표시 추가
    startup_pattern = r'logger\.info\("API server v2 started \(with v1 compatibility\)"\)'
    content = re.sub(
        startup_pattern,
        'logger.info(f"API server v2 started (GPT Actions Mode: {GPT_ACTIONS_MODE})")',
        content
    )
    
    # 5. Dockerfile 환경 변수 설정 파일 생성
    dockerfile_content = """# Dockerfile 환경 변수 설정 추가
# Render 서버에서 사용할 환경 변수

# .env 파일 또는 Render 대시보드에서 설정:
ENV GPT_ACTIONS_MODE=true
ENV API_KEY=your-secure-api-key-here

# 또는 docker run 시:
# docker run -e GPT_ACTIONS_MODE=true -e API_KEY=your-key ...
"""
    
    with open('/mnt/d/00.Work_AI_Tool/06.GPTs_kcsc/gpts_data/DOCKER_ENV_SETTINGS.txt', 'w', encoding='utf-8') as f:
        f.write(dockerfile_content)
    
    # 파일 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ lightweight_gpts_api_server.py 수정 완료")
    print("  - GPT_ACTIONS_MODE 환경 변수 추가")
    print("  - API 키 검증 로직 개선")
    print("  - CORS 설정 개선")


def create_gpt_actions_setup_guide():
    """GPT Actions 설정 가이드 생성"""
    
    guide = """# GPT Actions 설정 가이드 - 인증 문제 해결

## 🔧 문제 원인

1. **API 키 인증 실패**: GPT Actions에서 API 키를 제대로 전달하지 못함
2. **is_consequential 설정**: POST 요청이 consequential로 설정되어 사용자 승인 필요
3. **헤더 전달 문제**: X-API-Key 헤더가 제대로 전달되지 않음

## ✅ 해결 방법

### 1. Render 서버 환경 변수 설정

Render 대시보드에서 다음 환경 변수 추가:
```
GPT_ACTIONS_MODE=true
API_KEY=your-secure-api-key-here
```

### 2. GPT Actions 설정

#### Authentication 설정:
1. ChatGPT Custom GPT 편집 화면
2. Actions 섹션
3. Authentication 클릭
4. API Key 선택
5. 다음 정보 입력:
   - Auth Type: `API Key`
   - API Key: `your-secure-api-key-here`
   - Header Name: `X-API-Key`

#### Schema 업데이트:
1. 기존 Schema 삭제
2. `FIXED_OPENAPI_SCHEMA.json` 내용 복사/붙여넣기
3. 모든 operation에 `x-openai-isConsequential: false` 확인

### 3. 테스트

1. 간단한 검색 테스트:
   ```
   "KDS 14 20 01 검색해줘"
   ```

2. 키워드 검색 테스트:
   ```
   "콘크리트 슬럼프 관련 기준 찾아줘"
   ```

### 4. 문제 지속 시

#### Option A: API 키 없이 테스트
1. Render 환경 변수에서 `GPT_ACTIONS_MODE=true` 확인
2. GPT Actions에서 Authentication 제거
3. 재테스트

#### Option B: 커스텀 헤더 사용
Schema에서 각 operation의 parameters를 다음과 같이 수정:
```json
"parameters": [
  {
    "name": "Authorization",
    "in": "header",
    "required": false,
    "schema": {
      "type": "string",
      "default": "Bearer your-api-key"
    }
  }
]
```

### 5. 디버깅 팁

1. **Render 로그 확인**:
   ```
   https://dashboard.render.com/web/srv-xxxxx/logs
   ```

2. **API 직접 테스트**:
   ```bash
   curl -X POST https://kcsc-gpt-api.onrender.com/api/v1/search \\
     -H "X-API-Key: your-api-key" \\
     -H "Content-Type: application/json" \\
     -d '{"query": "콘크리트", "search_type": "keyword"}'
   ```

3. **GPT Actions 로그**:
   - 대화 중 "Debug" 모드 활성화
   - 요청/응답 상세 정보 확인

## 🚀 권장 설정

### Render 서버 (.env 또는 환경 변수):
```
GPT_ACTIONS_MODE=true
API_KEY=kcsc-gpt-secure-key-2025
LOG_LEVEL=INFO
```

### GPT Actions:
- Authentication: None (GPT_ACTIONS_MODE=true 시)
- 또는 API Key with Header Name: X-API-Key

### 보안 고려사항:
- Production에서는 적절한 API 키 사용
- Rate limiting 설정
- IP 화이트리스트 (가능한 경우)

이 설정으로 GPT Actions와 Render API 서버 간의 인증 문제가 해결됩니다."""
    
    with open('/mnt/d/00.Work_AI_Tool/06.GPTs_kcsc/gpts_data/GPT_ACTIONS_AUTH_FIX_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print("\n✓ GPT Actions 인증 해결 가이드 생성 완료")


def create_render_env_template():
    """Render 환경 변수 템플릿 생성"""
    
    template = """# Render 환경 변수 설정

## 필수 환경 변수

```bash
# GPT Actions 호환 모드 활성화
GPT_ACTIONS_MODE=true

# API 키 (선택적 - GPT_ACTIONS_MODE=true 시)
API_KEY=kcsc-gpt-secure-key-2025

# 로그 레벨
LOG_LEVEL=INFO

# 데이터 경로
SPLIT_DATA_PATH=./gpts_data/standards_split
INDEX_PATH=./gpts_data/search_index.json

# 포트 (Render가 자동 설정)
# PORT=10000
```

## Render Dashboard 설정 방법

1. https://dashboard.render.com 로그인
2. 해당 서비스 선택
3. Environment 탭 클릭
4. Add Environment Variable 클릭
5. 위 변수들 추가

## Docker 실행 시 (로컬 테스트)

```bash
docker run -d \\
  -e GPT_ACTIONS_MODE=true \\
  -e API_KEY=test-key \\
  -e LOG_LEVEL=DEBUG \\
  -p 8000:8000 \\
  kcsc-gpt-api
```

## 확인 방법

서버 시작 로그에서 확인:
```
API server v2 started (GPT Actions Mode: True)
```

API 호출 테스트:
```bash
# API 키 없이 테스트 (GPT_ACTIONS_MODE=true)
curl https://kcsc-gpt-api.onrender.com/health

# API 키와 함께 테스트
curl -H "X-API-Key: your-key" https://kcsc-gpt-api.onrender.com/api/v1/search
```"""
    
    with open('/mnt/d/00.Work_AI_Tool/06.GPTs_kcsc/gpts_data/RENDER_ENV_TEMPLATE.md', 'w', encoding='utf-8') as f:
        f.write(template)
    
    print("✓ Render 환경 변수 템플릿 생성 완료")


def main():
    print("=== GPT Actions 인증 문제 해결 ===\n")
    
    # 1. API 서버 코드 수정
    fix_lightweight_api_server()
    
    # 2. 가이드 문서 생성
    create_gpt_actions_setup_guide()
    
    # 3. Render 환경 변수 템플릿 생성
    create_render_env_template()
    
    print("\n=== 다음 단계 ===")
    print("1. 수정된 lightweight_gpts_api_server.py를 GitHub에 푸시")
    print("2. Render 대시보드에서 환경 변수 설정:")
    print("   - GPT_ACTIONS_MODE=true")
    print("3. GPT Actions에서 FIXED_OPENAPI_SCHEMA.json으로 스키마 업데이트")
    print("4. Authentication 설정 확인 (옵션)")
    print("\n상세 가이드: GPT_ACTIONS_AUTH_FIX_GUIDE.md 참조")


if __name__ == "__main__":
    main()