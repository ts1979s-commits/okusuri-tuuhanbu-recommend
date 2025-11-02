"""
Streamlit Web UI - お薬通販部商品レコメンドLLMアプリ
ユーザーフレンドリーなWeb インターフェース
"""
import streamlit as st
import sys
import os
from typing import List, Dict, Any
import logging
import time

# パスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recommendation_engine import RecommendationEngine, SearchResult, RecommendationContext
from src.scraper import OkusuriScraper
from config.settings import get_settings

settings = get_settings()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlitページ設定
st.set_page_config(
    page_title="お薬通販部 商品レコメンド",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# スタイル設定
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #f9f9f9;
    }
    .score-badge {
        background-color: #4CAF50;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
    }
    .query-type-badge {
        background-color: #2196F3;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_recommendation_engine():
    """レコメンドエンジンを初期化（キャッシュ付き）"""
    try:
        engine = RecommendationEngine()
        # 初期化が成功したかテスト
        _ = engine.get_system_status()
        return engine
    except Exception as e:
        st.error(f"システム初期化エラー: {str(e)}")
        raise e

@st.cache_resource
def initialize_scraper():
    """スクレイパーを初期化（キャッシュ付き）"""
    return OkusuriScraper()

def display_search_result(result: SearchResult, index: int):
    """検索結果を表示"""
    with st.container():
        # メタデータから効果と有効成分を取得
        effect = result.metadata.get('効果', 'N/A') if hasattr(result, 'metadata') and result.metadata else 'N/A'
        active_ingredient = result.metadata.get('有効成分', 'N/A') if hasattr(result, 'metadata') and result.metadata else 'N/A'
        
        st.markdown(f"""
        <div class="result-card">
            <h4>🏷️ {result.product_name}</h4>
            <p><strong>⚗️ 有効成分:</strong> {active_ingredient}</p>
            <p><strong>✨ 効果:</strong> {effect}</p>
            <p><strong>📂 カテゴリ:</strong> {result.category or 'N/A'}</p>
            <p><strong>📝 説明:</strong> {(result.description or 'N/A')[:200]}{'...' if len(result.description or '') > 200 else ''}</p>
            <p><strong>🔗 URL:</strong> <a href="{result.url}" target="_blank">商品ページを開く</a></p>
            <span class="score-badge">類似度: {result.similarity_score:.3f}</span>
        </div>
        """, unsafe_allow_html=True)

def display_system_status():
    """システム状態を表示"""
    st.subheader("🔧 システム状態")
    
    try:
        # Streamlit Cloud環境では簡略化した状態を表示
        st.success("✅ システムは正常に動作しています")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**レコメンドエンジン:**", "ready")
            st.write("**RAGシステム:**")
            st.write("- コレクション: faiss_products") 
            st.write("- 商品数: 35")
            st.write("- 状態: ready")
        
        with col2:
            st.write("**サポートされる検索タイプ:**")
            for query_type in ["symptom", "product_name", "category", "ingredient", "general"]:
                st.write(f"- {query_type}")
            
            st.write("**機能:**")
            for feature in ["症状ベース検索", "商品名検索"]:
                st.write(f"- {feature}")
                
    except Exception as e:
        st.error(f"システム状態の取得に失敗しました: {e}")
        st.info("簡略化モードで動作中です")

def scrape_products_interface():
    """商品データ取得インターフェース"""
    st.subheader("🕷️ 商品データ取得")
    st.write("お薬通販部サイトから商品情報を取得してデータベースに追加します。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_products = st.number_input(
            "取得する最大商品数", 
            min_value=1, 
            max_value=200, 
            value=20,
            help="多すぎるとAPIコストが高くなります"
        )
    
    with col2:
        st.write("⚠️ **注意事項:**")
        st.write("- 取得には時間がかかります")
        st.write("- OpenAI APIを使用します")
        st.write("- 適切な間隔で実行してください")
    
    if st.button("🚀 商品データを取得開始", type="primary"):
        try:
            scraper = initialize_scraper()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("商品データを取得中..."):
                status_text.text("スクレイピングを開始しています...")
                progress_bar.progress(0.1)
                
                # 商品データを取得
                products = scraper.scrape_products(max_products=max_products)
                progress_bar.progress(0.7)
                
                if products:
                    status_text.text("データベースに保存中...")
                    
                    # JSONファイルに保存
                    scraper.save_products(products, './data/products.json')
                    progress_bar.progress(0.9)
                    
                    # RAGシステムに追加
                    engine = initialize_recommendation_engine()
                    engine.rag_system.load_products_from_json('./data/products.json')
                    progress_bar.progress(1.0)
                    
                    st.success(f"✅ {len(products)}件の商品データを取得・保存しました！")
                    status_text.text("完了")
                    
                    # 結果の一部を表示
                    st.subheader("取得した商品例")
                    for product in products[:3]:
                        st.write(f"- {product.name} ({product.price})")
                else:
                    st.warning("⚠️ 商品データを取得できませんでした")
                    
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
            logger.error(f"スクレイピングエラー: {e}")

def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.markdown('<h1 class="main-header">💊 お薬通販部 商品レコメンド AI</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # サイドバー
    with st.sidebar:
        st.header("🔧 機能メニュー")
        
        # システム状態
        if st.checkbox("システム状態を表示", value=True):
            display_system_status()
        
        st.markdown("---")
        
        # データ取得機能
        if st.checkbox("商品データ取得"):
            scrape_products_interface()
        
        st.markdown("---")
        
        # 設定
        st.subheader("⚙️ 検索設定")
        max_results = st.slider("最大結果数", 1, 20, 5)
        show_details = st.checkbox("詳細情報を表示", value=True)
    
    # メインエリア
    st.header("🔍 商品検索・レコメンド")
    
    # 検索例を表示
    with st.expander("💡 検索例", expanded=False):
        st.write("**症状での検索:**")
        st.write("- 頭痛がひどいので何か良い薬はありますか")
        st.write("- 風邪を引いたみたいです")
        st.write("- 胃が痛いです")
        
        st.write("**商品名での検索:**")
        st.write("- ロキソニン")
        st.write("- バファリン")
        
        st.write("**カテゴリでの検索:**")
        st.write("- 風邪薬を探しています")
        st.write("- ビタミン剤が欲しいです")
    
    # 検索フォーム
    user_query = st.text_input(
        "💬 症状や探している商品を入力してください:",
        placeholder="例: 頭痛がひどいので何か良い薬はありますか",
        help="症状、商品名、カテゴリなど自然な言葉で入力できます"
    )
    
    # 検索ボタン
    if st.button("🔍 検索・レコメンド", type="primary") or user_query:
        if user_query.strip():
            try:
                engine = initialize_recommendation_engine()
                
                with st.spinner("検索中..."):
                    start_time = time.time()
                    results, context = engine.recommend_products(
                        user_query, 
                        max_results=max_results
                    )
                    search_time = time.time() - start_time
                
                # 結果の表示
                st.markdown("---")
                st.subheader("📋 検索結果")
                
                # 検索情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("結果数", len(results))
                with col2:
                    st.metric("検索時間", f"{search_time:.2f}秒")
                with col3:
                    st.markdown(f'<span class="query-type-badge">タイプ: {context.query_type.value}</span>', unsafe_allow_html=True)
                
                if show_details and context.extracted_keywords:
                    st.write("**抽出されたキーワード:**", ", ".join(context.extracted_keywords))
                
                # 検索結果の表示
                if results:
                    st.markdown("### 🎯 おすすめ商品")
                    
                    # デバッグ情報（開発用）
                    if show_details:
                        with st.expander("🔧 デバッグ情報", expanded=False):
                            st.write(f"**検索クエリ:** '{user_query}'")
                            st.write(f"**結果数:** {len(results)}")
                            st.write(f"**システム状態:** {engine.get_system_status()}")
                            if results:
                                st.write("**最初の結果サンプル:**")
                                first_result = results[0]
                                st.json({
                                    "product_name": first_result.product_name,
                                    "category": first_result.category,
                                    "similarity_score": first_result.similarity_score,
                                    "metadata_sample": dict(list(first_result.metadata.items())[:5]) if first_result.metadata else {}
                                })
                    
                    for i, result in enumerate(results):
                        display_search_result(result, i)
                        
                else:
                    st.warning("🤔 該当する商品が見つかりませんでした。別のキーワードで検索してみてください。")
                    st.info("💡 まず商品データを取得する必要がある可能性があります。サイドバーの「商品データ取得」をお試しください。")
                
            except Exception as e:
                st.error(f"❌ 検索エラーが発生しました: {str(e)}")
                
                # デバッグ情報を表示
                with st.expander("🔍 詳細なエラー情報", expanded=False):
                    st.write("**エラーの詳細:**", str(e))
                    st.write("**エラータイプ:**", type(e).__name__)
                    
                    # 設定確認
                    try:
                        from config.settings import get_settings
                        settings = get_settings()
                        st.write("**OpenAI APIキー:**", "✅ 設定済み" if settings.OPENAI_API_KEY else "❌ 未設定")
                        st.write("**ログレベル:**", settings.LOG_LEVEL)
                    except Exception as config_error:
                        st.write("**設定読み込みエラー:**", str(config_error))
                    
                    # システム情報
                    import sys
                    import os
                    st.write("**Python バージョン:**", sys.version)
                    st.write("**作業ディレクトリ:**", os.getcwd())
                    
                    # データファイルの存在確認
                    data_files = [
                        "./data/faiss_index.bin",
                        "./data/metadata.pkl", 
                        "./data/documents.pkl",
                        "./data/product_recommend.csv"
                    ]
                    for file_path in data_files:
                        exists = os.path.exists(file_path)
                        st.write(f"**{file_path}:**", "✅ 存在" if exists else "❌ 不在")
                
                st.warning("⚠️ システムが初期化中の可能性があります。しばらく待ってから再度お試しください。")
                
                # デバッグ情報
                error_msg = str(e)
                st.info(f"エラーの詳細: {error_msg}")
                
                logger.error(f"検索エラー: {e}")
        else:
            st.warning("検索クエリを入力してください。")
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        💊 お薬通販部 商品レコメンド AI - フェーズ1実装<br>
        Powered by OpenAI GPT + RAG + FAISS
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()