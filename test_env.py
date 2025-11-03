#!/usr/bin/env python3
"""
環境変数とAPI設定をテストするスクリプト
"""
import os
from dotenv import load_dotenv

def test_env_vars():
    print("=== 環境変数テスト ===")
    
    # .envファイルを読み込み
    print("1. .envファイル読み込み...")
    load_dotenv()
    
    # OpenAI APIキーをチェック
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"✅ OPENAI_API_KEY: {api_key[:10]}...{api_key[-10:] if len(api_key) > 20 else api_key}")
    else:
        print("❌ OPENAI_API_KEY: 未設定")
    
    # その他の環境変数
    print(f"🔧 作業ディレクトリ: {os.getcwd()}")
    print(f"🔧 .envファイル存在: {os.path.exists('.env')}")
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            print(f"🔧 .envファイル内容: {len(content)} 文字")
            lines = content.strip().split('\n')
            for line in lines:
                if '=' in line:
                    key = line.split('=')[0]
                    print(f"   - {key}")

if __name__ == "__main__":
    test_env_vars()