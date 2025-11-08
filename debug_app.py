"""
最小限のStreamlit Cloud対応アプリ - 段階的デバッグ用
"""
import streamlit as st
import sys
import os

# Streamlitページ設定
st.set_page_config(
    page_title="お薬通販部 商品レコメンド",
    page_icon="💊",
    layout="wide"
)

def main():
    st.title("💊 お薬通販部 商品レコメンド AI")
    st.write("システム診断中...")
    
    # 1. 基本的なPython環境チェック
    st.subheader("🔍 システム診断")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Python情報:**")
        st.write(f"- Python バージョン: {sys.version.split()[0]}")
        st.write(f"- Python パス: {sys.executable}")
        st.write(f"- 現在のディレクトリ: {os.getcwd()}")
    
    with col2:
        st.write("**ファイル確認:**")
        # 重要なファイルの存在確認
        files_to_check = [
            "data/product_recommend.csv",
            "src/__init__.py",
            "src/faiss_rag_system.py",
            "config/__init__.py",
            "config/settings.py"
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                st.write(f"✅ {file_path}")
            else:
                st.write(f"❌ {file_path}")
    
    # 2. 環境変数の確認
    st.subheader("🔑 環境変数確認")
    
    # OpenAI APIキーの確認（セキュアに）
    try:
        openai_key = st.secrets.get("secrets", {}).get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
        if openai_key:
            key_display = openai_key[:8] + "..." if len(openai_key) > 8 else "短すぎます"
            st.success(f"✅ OpenAI API Key found: {key_display}")
        else:
            st.error("❌ OpenAI API Key not found")
            st.code("""
[secrets]
OPENAI_API_KEY = "sk-your-api-key"
            """)
    except Exception as e:
        st.error(f"❌ Secrets読み込みエラー: {e}")
    
    # 3. ライブラリのインポートテスト
    st.subheader("📦 ライブラリ確認")
    
    import_tests = [
        ("numpy", "import numpy as np"),
        ("pandas", "import pandas as pd"),
        ("streamlit", "import streamlit as st"),
        ("openai", "import openai"),
        ("faiss", "import faiss"),
    ]
    
    for lib_name, import_cmd in import_tests:
        try:
            exec(import_cmd)
            st.success(f"✅ {lib_name}")
        except ImportError as e:
            st.error(f"❌ {lib_name}: {e}")
        except Exception as e:
            st.warning(f"⚠️ {lib_name}: {e}")
    
    # 4. カスタムモジュールのテスト
    st.subheader("🏗️ カスタムモジュール確認")
    
    # パスを追加
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        # 設定モジュールのテスト
        try:
            from config.settings import get_settings
            settings = get_settings()
            st.success("✅ config.settings")
        except Exception as e:
            st.warning(f"⚠️ config.settings: {e}")
            st.info("代替設定を使用します")
        
        # FAISSシステムのテスト
        try:
            from src.faiss_rag_system import FAISSRAGSystem
            st.success("✅ src.faiss_rag_system")
            
            # 実際に初期化を試行
            with st.spinner("RAGシステム初期化テスト中..."):
                rag = FAISSRAGSystem()
                st.success("✅ RAGシステム初期化成功")
                
                # 簡単な検索テスト
                if st.button("🔍 テスト検索実行"):
                    with st.spinner("検索テスト中..."):
                        try:
                            results = rag.search_products("テスト", top_k=3)
                            if results:
                                st.success(f"✅ 検索成功: {len(results)}件の結果")
                                for i, result in enumerate(results[:2], 1):
                                    st.write(f"{i}. {result.product_name}")
                            else:
                                st.info("検索結果なし（正常）")
                        except Exception as e:
                            st.error(f"❌ 検索エラー: {e}")
                            
        except Exception as e:
            st.error(f"❌ src.faiss_rag_system: {e}")
            st.write("詳細エラー:")
            st.exception(e)
    
    except Exception as e:
        st.error(f"❌ モジュールテストエラー: {e}")
    
    # 5. 簡単な検索インターフェース
    if st.checkbox("🚀 簡単な検索を有効化", value=False):
        st.subheader("🔍 簡易検索")
        query = st.text_input("検索クエリ:", placeholder="サプリメント")
        
        if st.button("検索") and query:
            st.info(f"「{query}」で検索中...")
            try:
                # ここで実際の検索を実装
                st.success("検索機能は診断モードでは無効化されています")
            except Exception as e:
                st.error(f"検索エラー: {e}")

if __name__ == "__main__":
    main()