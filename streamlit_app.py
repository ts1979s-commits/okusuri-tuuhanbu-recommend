"""
お薬通販部 商品レコメンド AI - Streamlit Cloud対応版
"""
import streamlit as st
import os
import sys

# ページ設定
st.set_page_config(
    page_title="お薬通販部レコメンド",
    page_icon="💊",
    layout="wide"
)

def main():
    st.title("💊 お薬通販部 商品レコメンド AI")
    
    # ステップ1: 環境確認
    with st.expander("🔧 システム状態", expanded=True):
        # OpenAI APIキー確認
        try:
            # Streamlit secretsから取得
            openai_key = None
            if 'secrets' in st.secrets and 'OPENAI_API_KEY' in st.secrets['secrets']:
                openai_key = st.secrets['secrets']['OPENAI_API_KEY']
            elif 'OPENAI_API_KEY' in st.secrets:
                openai_key = st.secrets['OPENAI_API_KEY']
            
            if openai_key and openai_key.startswith('sk-'):
                st.success("✅ OpenAI APIキー設定済み")
                key_ok = True
            else:
                st.error("❌ OpenAI APIキーが設定されていません")
                st.code("""
Streamlit Cloud の Settings → Secrets で設定してください:

[secrets]
OPENAI_API_KEY = "sk-your-actual-api-key"
                """)
                key_ok = False
        except Exception as e:
            st.error(f"設定読み込みエラー: {e}")
            key_ok = False
        
        # 必要なファイル確認
        required_files = ["data/product_recommend.csv"]
        files_ok = True
        for file_path in required_files:
            if os.path.exists(file_path):
                st.success(f"✅ {file_path}")
            else:
                st.error(f"❌ {file_path}")
                files_ok = False
    
    if not key_ok:
        st.stop()
    
    # ステップ2: システム初期化
    try:
        # パス設定
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # モジュールのインポート
        with st.spinner("システム初期化中..."):
            from src.faiss_rag_system import FAISSRAGSystem
            
            @st.cache_resource
            def init_system():
                return FAISSRAGSystem()
            
            rag_system = init_system()
        
        st.success("✅ システム初期化完了")
        
    except Exception as e:
        st.error(f"❌ システム初期化失敗: {e}")
        st.exception(e)
        st.stop()
    
    # ステップ3: 検索インターフェース
    st.header("🔍 商品検索")
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        max_results = st.slider("最大結果数", 1, 10, 5)
        
        st.header("💡 検索例")
        examples = [
            "サプリメント",
            "ED治療薬",
            "AGA治療薬",
            "美容・スキンケア",
            "ダイエット",
            "カマグラゴールド",
            "トリファラ"
        ]
        
        for example in examples:
            if st.button(f"「{example}」", key=f"ex_{example}"):
                st.session_state['search_query'] = example
    
    # 検索フォーム
    query = st.text_input(
        "検索クエリを入力:",
        value=st.session_state.get('search_query', ''),
        placeholder="例: サプリメント",
        key='main_search'
    )
    
    if st.button("🔍 検索", type="primary") and query.strip():
        with st.spinner(f"「{query}」を検索中..."):
            try:
                results = rag_system.search_products(query, top_k=max_results)
                
                if results:
                    st.success(f"🎯 {len(results)}件の商品が見つかりました")
                    
                    for i, result in enumerate(results, 1):
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.subheader(f"{i}. {result.product_name}")
                                
                                if hasattr(result, 'category') and result.category:
                                    st.write(f"📂 **カテゴリ:** {result.category}")
                                
                                if hasattr(result, 'metadata') and result.metadata:
                                    effect = result.metadata.get('effect', '')
                                    ingredient = result.metadata.get('ingredient', '')
                                    if effect:
                                        st.write(f"✨ **効果:** {effect}")
                                    if ingredient:
                                        st.write(f"⚗️ **成分:** {ingredient}")
                                
                                if hasattr(result, 'description') and result.description:
                                    desc = result.description[:200] + "..." if len(result.description) > 200 else result.description
                                    st.write(f"📝 **説明:** {desc}")
                            
                            with col2:
                                if hasattr(result, 'similarity_score'):
                                    score = result.similarity_score
                                    st.metric("類似度", f"{score:.3f}")
                                
                                if hasattr(result, 'url') and result.url:
                                    st.link_button("🔗 商品ページ", result.url)
                        
                        st.divider()
                else:
                    st.warning("🤔 該当する商品が見つかりませんでした")
                    st.info("💡 別のキーワードで検索してみてください")
                    
            except Exception as e:
                st.error(f"❌ 検索エラー: {e}")
                st.exception(e)
    
    # フッター
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "💊 お薬通販部 商品レコメンド AI<br>"
        "Powered by OpenAI + FAISS"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()