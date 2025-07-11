#!/usr/bin/env python3
"""
Commentator 프로젝트 환경 설정 스크립트
가상환경 생성 및 패키지 설치를 자동화합니다.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """명령어를 실행하고 결과를 출력합니다."""
    print(f"\n🔄 {description}...")
    print(f"실행 명령어: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} 완료!")
        if result.stdout:
            print(f"출력: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 실패!")
        print(f"오류: {e.stderr}")
        return False

def check_python_version():
    """Python 버전을 확인합니다."""
    version = sys.version_info
    print(f"🐍 Python 버전: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 이상이 필요합니다!")
        return False
    
    print("✅ Python 버전이 적절합니다.")
    return True

def create_virtual_environment():
    """가상환경을 생성합니다."""
    venv_name = "commentator_env"
    
    if Path(venv_name).exists():
        print(f"⚠️  가상환경 '{venv_name}'이 이미 존재합니다.")
        response = input("기존 가상환경을 삭제하고 새로 만들까요? (y/N): ")
        if response.lower() == 'y':
            run_command(f"rm -rf {venv_name}", "기존 가상환경 삭제")
        else:
            print("기존 가상환경을 사용합니다.")
            return venv_name
    
    print(f"\n📦 가상환경 '{venv_name}'을 생성합니다...")
    if run_command(f"python -m venv {venv_name}", "가상환경 생성"):
        return venv_name
    return None

def get_activate_command(venv_name):
    """운영체제에 따른 가상환경 활성화 명령어를 반환합니다."""
    system = platform.system().lower()
    
    if system == "windows":
        return f"{venv_name}\\Scripts\\activate"
    else:
        return f"source {venv_name}/bin/activate"

def install_packages(venv_name):
    """필요한 패키지들을 설치합니다."""
    activate_cmd = get_activate_command(venv_name)
    
    # pip 업그레이드
    if not run_command(f"{activate_cmd} && pip install --upgrade pip", "pip 업그레이드"):
        return False
    
    # requirements.txt 설치
    if Path("requirements.txt").exists():
        if not run_command(f"{activate_cmd} && pip install -r requirements.txt", "패키지 설치"):
            return False
    else:
        print("❌ requirements.txt 파일을 찾을 수 없습니다!")
        return False
    
    return True

def create_env_file():
    """환경변수 파일을 생성합니다."""
    env_content = """# OpenSearch 설정
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin
OPENSEARCH_INDEX_NAME=bing_articles

# Telegram Bot 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 데이터 수집 설정
BING_API_KEY=your_bing_api_key_here
NEWS_API_KEY=your_news_api_key_here

# LLM 설정 (로컬 추론용)
LLM_MODEL_PATH=/path/to/your/local/model
LLM_DEVICE=cuda
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.7

# 벡터 DB 설정
VECTOR_DIMENSION=1536
EMBEDDING_MODEL=text-embedding-ada-002

# 애플리케이션 설정
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=true

# 데이터베이스 설정 (필요시)
DATABASE_URL=sqlite:///./commentator.db

# 보안 설정
SECRET_KEY=your_secret_key_here
"""
    
    env_file = Path('.env')
    if not env_file.exists():
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            print("✅ .env 파일이 생성되었습니다!")
        except Exception as e:
            print(f"❌ .env 파일 생성 실패: {e}")
    else:
        print("✅ .env 파일이 이미 존재합니다.")

def main():
    print("🎙️ Commentator 프로젝트 환경 설정")
    print("=" * 50)
    
    # Python 버전 확인
    if not check_python_version():
        sys.exit(1)
    
    # 가상환경 생성
    venv_name = create_virtual_environment()
    if not venv_name:
        print("❌ 가상환경 생성에 실패했습니다.")
        sys.exit(1)
    
    # 패키지 설치
    if not install_packages(venv_name):
        print("❌ 패키지 설치에 실패했습니다.")
        sys.exit(1)
    
    # 환경변수 파일 생성
    create_env_file()
    
    # 완료 메시지
    print("\n🎉 환경 설정이 완료되었습니다!")
    print("\n📋 다음 단계:")
    print("1. 가상환경 활성화:")
    activate_cmd = get_activate_command(venv_name)
    print(f"   {activate_cmd}")
    print("\n2. .env 파일을 수정하여 필요한 API 키들을 설정하세요")
    print("\n3. OpenSearch 시작:")
    print("   docker-compose up -d")
    print("\n4. 각 모듈 테스트:")
    print("   - 데이터 수집: python data_collection/news_crawl.py")
    print("   - 벡터 DB: python vectorDB/convert_and_upload.py")
    print("   - 텔레그램 봇: python io/TelegramLlmBot.py")

if __name__ == "__main__":
    main() 