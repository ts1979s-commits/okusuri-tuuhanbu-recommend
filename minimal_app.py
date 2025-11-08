"""
お薬通販部 商品レコメンド AI - 最小版
"""
import streamlit as st
import os
import sys
import traceback

# ページ設定
st.set_page_config(
    page_title="お薬通販部レコメンド",
    page_icon="💊"
)

def main():
    st.title("💊 お薬通販部 商品レコメンド AI")
    
    # デバッグ情報表示
    if st.checkbox("🔧 デバッグ情報を表示", value=True):
        with st.expander("システム情報", expanded=False):
            st.write(f"Python: {sys.version}")
            st.write(f"作業ディレクトリ: {os.getcwd()}")
            st.write(f"Pythonパス: {sys.path[:3]}...")
    
    # API キー確認
    try:
        # Streamlit Secrets からOpenAI API キーを取得
        api_key = None
        
        # 複数の方法で取得を試行
        if hasattr(st, 'secrets'):
            try:
                if 'secrets' in st.secrets:
                    api_key = st.secrets['secrets'].get('OPENAI_API_KEY')
                if not api_key:
                    api_key = st.secrets.get('OPENAI_API_KEY')
            except Exception as e:
                st.error(f"Secrets読み込みエラー: {e}")
        
        if api_key and api_key.startswith('sk-'):
            st.success("✅ OpenAI APIキー設定確認")
            api_key_ok = True
        else:
            st.error("❌ OpenAI APIキーが設定されていません")
            st.info("""
            Streamlit Cloud の Settings → Secrets で以下を設定してください:
            
            ```
            [secrets]
            OPENAI_API_KEY = "sk-your-api-key"
            ```
            
            または
            
            ```
            OPENAI_API_KEY = "sk-your-api-key"
            ```
            """)
            api_key_ok = False
    except Exception as e:
        st.error(f"設定確認エラー: {e}")
        api_key_ok = False
    
    if not api_key_ok:
        st.warning("⚠️ APIキーを設定してから再度お試しください")
        return
    
    # システム初期化
    st.write("---")
    st.subheader("🔧 システム初期化")
    
    try:
        with st.spinner("モジュールを読み込み中..."):
            # パス設定
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            # 段階的にモジュールをインポート
            try:
                import numpy as np
                st.success("✅ numpy")
            except Exception as e:
                st.error(f"❌ numpy: {e}")
                return
            
            try:
                import pandas as pd
                st.success("✅ pandas")
            except Exception as e:
                st.error(f"❌ pandas: {e}")
                return
            
            try:
                import faiss
                st.success("✅ faiss")
            except Exception as e:
                st.error(f"❌ faiss: {e}")
                return
            
            try:
                from openai import OpenAI
                st.success("✅ openai")
            except Exception as e:
                st.error(f"❌ openai: {e}")
                return
            
            # カスタムモジュールのインポート
            try:
                from src.faiss_rag_system import FAISSRAGSystem
                st.success("✅ FAISSRAGSystem")
            except Exception as e:
                st.error(f"❌ FAISSRAGSystem: {e}")
                st.error("詳細:")
                st.text(traceback.format_exc())
                return
        
        # RAGシステムの初期化
        with st.spinner("RAGシステムを初期化中..."):
            @st.cache_resource
            def init_rag():
                return FAISSRAGSystem()
            
            rag_system = init_rag()
            st.success("✅ RAGシステム初期化完了")
    
    except Exception as e:
        st.error(f"❌ 初期化エラー: {e}")
        st.error("詳細:")
        st.text(traceback.format_exc())
        return
    
    # 検索インターフェース
    st.write("---")
    st.subheader("🔍 商品検索")
    
    # 簡単な検索例
    col1, col2 = st.columns(2)
    with col1:
        if st.button("サプリメント"):
            st.session_state['search_query'] = "サプリメント"
        if st.button("ED治療薬"):
            st.session_state['search_query'] = "ED治療薬"
    
    with col2:
        if st.button("AGA治療薬"):
            st.session_state['search_query'] = "AGA治療薬"
        if st.button("美容・スキンケア"):
            st.session_state['search_query'] = "美容・スキンケア"
    
    # 検索入力
    query = st.text_input(
        "検索キーワード:",
        value=st.session_state.get('search_query', ''),
        placeholder="商品名や症状を入力",
        key='search_input'
    )
    
    if st.button("🔍 検索", type="primary") and query.strip():
        with st.spinner(f"「{query}」を検索中..."):
            try:
                # 検索実行
                results = rag_system.search_products(query, top_k=5)
                
                if results:
                    st.success(f"🎯 {len(results)}件の商品が見つかりました")
                    
                    for i, result in enumerate(results, 1):
                        st.write(f"**{i}. {result.product_name}**")
                        
                        if hasattr(result, 'category') and result.category:
                            st.write(f"📂 カテゴリ: {result.category}")
                        
                        if hasattr(result, 'metadata') and result.metadata:
                            effect = result.metadata.get('effect', '')
                            if effect:
                                st.write(f"✨ 効果: {effect}")
                        
                        if hasattr(result, 'similarity_score'):
                            st.write(f"📊 類似度: {result.similarity_score:.3f}")
                        
                        if hasattr(result, 'url') and result.url:
                            st.write(f"🔗 [商品ページを開く]({result.url})")
                        
                        st.write("---")
                else:
                    st.warning("🤔 該当する商品が見つかりませんでした")
                    st.info("💡 別のキーワードで検索してみてください")
            
            except Exception as e:
                st.error(f"❌ 検索エラー: {e}")
                st.text(traceback.format_exc())
    
    # フッター
    st.write("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "💊 お薬通販部 商品レコメンド AI<br>"
        "Powered by OpenAI + FAISS"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()