"""
Streamlit Web UI - お薬通販部商品レコメンドLLMアプリ
Streamlit Cloud 対応版
"""
import streamlit as st
import os
import sys
import logging
from typing import List, Optional

# パスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Streamlitページ設定
st.set_page_config(
    page_title="お薬通販部 商品レコメンド",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.markdown("""
    <h1 style="text-align: center; color: #1f77b4; margin-bottom: 2rem;">
        💊 お薬通販部 商品レコメンド AI
    </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    # OpenAI API キーの確認
    try:
        openai_api_key = st.secrets.get("secrets", {}).get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
        if not openai_api_key:
            st.error("🔑 OpenAI API キーが設定されていません")
            st.info("Streamlit Cloud の Secrets で OPENAI_API_KEY を設定してください")
            st.code("""
[secrets]
OPENAI_API_KEY = "sk-..."
""")
            return
    except Exception as e:
        st.error(f"設定の読み込みエラー: {e}")
        return
    
    # システム初期化
    with st.spinner("システムを初期化中..."):
        try:
            from src.faiss_rag_system import FAISSRAGSystem
            
            # RAGシステムの初期化
            @st.cache_resource
            def init_rag_system():
                return FAISSRAGSystem()
            
            rag_system = init_rag_system()
            st.success("✅ システム初期化完了")
            
        except Exception as e:
            st.error(f"❌ システム初期化エラー: {e}")
            st.info("以下を確認してください：")
            st.write("1. すべての依存関係がインストールされているか")
            st.write("2. CSVデータファイルが存在するか")
            st.write("3. OpenAI APIキーが正しく設定されているか")
            return
    
    # サイドバー
    with st.sidebar:
        st.header("🔧 検索設定")
        max_results = st.slider("最大結果数", 1, 20, 5)
        
        st.header("💡 検索例")
        st.write("**症状での検索:**")
        st.write("- 抜け毛が増えた")
        st.write("- むくみを取りたい")
        
        st.write("**商品名での検索:**")
        st.write("- カマグラゴールド")
        st.write("- トリファラ")
        
        st.write("**カテゴリでの検索:**")
        st.write("- ED治療薬")
        st.write("- サプリメント")
    
    # メイン検索エリア
    st.header("🔍 商品検索・レコメンド")
    
    user_query = st.text_input(
        "💬 症状や探している商品を入力してください:",
        placeholder="例: サプリメントを探しています",
        help="症状、商品名、カテゴリなど自然な言葉で入力できます"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_button = st.button("🔍 検索・レコメンド", type="primary")
    with col2:
        if st.button("🔄 リフレッシュ"):
            st.cache_resource.clear()
            st.rerun()
    
    # 検索実行
    if search_button and user_query.strip():
        with st.spinner("検索中..."):
            try:
                results = rag_system.search_products(user_query, top_k=max_results)
                
                if results:
                    st.markdown("---")
                    st.subheader("📋 検索結果")
                    
                    # 結果統計
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("結果数", len(results))
                    with col2:
                        st.metric("検索方式", "AI検索")
                    
                    # 検索結果の表示
                    for i, result in enumerate(results, 1):
                        with st.expander(f"{i}. {result.product_name}", expanded=i <= 3):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"**📂 カテゴリ:** {result.category or 'N/A'}")
                                
                                # メタデータの表示
                                if hasattr(result, 'metadata') and result.metadata:
                                    effect = result.metadata.get('effect', 'N/A')
                                    ingredient = result.metadata.get('ingredient', 'N/A')
                                    st.write(f"**⚗️ 有効成分:** {ingredient}")
                                    st.write(f"**✨ 効果:** {effect}")
                                
                                if result.description:
                                    st.write(f"**📝 説明:** {result.description[:200]}{'...' if len(result.description) > 200 else ''}")
                            
                            with col2:
                                if hasattr(result, 'similarity_score'):
                                    score = result.similarity_score
                                    color = "#4CAF50" if score > 0.8 else "#FF9800" if score > 0.6 else "#F44336"
                                    st.markdown(f"""
                                    <div style="
                                        background-color: {color}; 
                                        color: white; 
                                        padding: 0.5rem; 
                                        border-radius: 10px; 
                                        text-align: center;
                                    ">
                                        類似度<br><strong>{score:.3f}</strong>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                if result.url:
                                    st.link_button("🔗 商品ページ", result.url)
                else:
                    st.warning("🤔 該当する商品が見つかりませんでした。")
                    st.info("💡 別のキーワードで検索してみてください。")
                    
            except Exception as e:
                st.error(f"❌ 検索エラー: {e}")
                st.info("しばらく時間をおいてから再試行してください。")
    
    elif search_button:
        st.warning("検索クエリを入力してください。")
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        💊 お薬通販部 商品レコメンド AI<br>
        Powered by OpenAI + RAG + FAISS
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()