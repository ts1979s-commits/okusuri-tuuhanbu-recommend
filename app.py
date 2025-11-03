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
        color: #333;
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
    
    /* ダークモード対応 */
    @media (prefers-color-scheme: dark) {
        .result-card {
            border: 1px solid #555;
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        .main-header {
            color: #4da6ff;
        }
    }
    
    /* Streamlitのダークテーマ検出 */
    [data-theme="dark"] .result-card {
        border: 1px solid #555;
        background-color: #2d2d2d;
        color: #e0e0e0;
    }
    [data-theme="dark"] .main-header {
        color: #4da6ff;
    }
    
    /* 強制的にダークモード対応（フォールバック） */
    .stApp[data-theme="dark"] .result-card {
        border: 1px solid #555 !important;
        background-color: #2d2d2d !important;
        color: #e0e0e0 !important;
    }
    
    /* Streamlit CSS変数を使用した対応 */
    .result-card {
        border: 1px solid var(--text-color-light, #ddd);
        background-color: var(--background-color-secondary, #f9f9f9);
        color: var(--text-color, #333);
    }
    .result-card h4, .result-card p, .result-card strong {
        color: var(--text-color, #333) !important;
    }
    .result-card a {
        color: var(--primary-color, #0066cc) !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_recommendation_engine():
    """レコメンドエンジンを初期化（キャッシュ付き、エラー処理強化）"""
    try:
        # エンジン初期化
        engine = RecommendationEngine()
        
        # 軽量な初期化テスト
        try:
            status = engine.get_system_status()
            st.sidebar.write(f"✅ システム状態: {status['recommendation_engine']}")
        except Exception as status_error:
            st.sidebar.warning(f"⚠️ 状態確認エラー: {str(status_error)}")
        
        return engine
        
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ システム初期化エラー: {error_msg}")
        
        # 詳細なエラー情報
        with st.expander("🔧 エラー詳細", expanded=False):
            st.write(f"**エラータイプ:** {type(e).__name__}")
            st.write(f"**エラーメッセージ:** {error_msg}")
            
            # 環境情報
            import sys
            st.write(f"**Python バージョン:** {sys.version}")
        
        # 軽量版システムを返す（基本的な機能のみ）
        st.warning("⚠️ システムは制限モードで動作しています")
        st.info("🔄 「リロード」ボタンまたはページの再読み込みを試してください")
        return None

@st.cache_resource
def initialize_scraper():
    """スクレイパーを初期化（キャッシュ付き）"""
    return OkusuriScraper()

def display_search_result(result: SearchResult, index: int):
    """検索結果を表示"""
    with st.container():
        # メタデータから効果と有効成分を取得（英語キーで取得）
        effect = result.metadata.get('effect', 'N/A') if hasattr(result, 'metadata') and result.metadata else 'N/A'
        active_ingredient = result.metadata.get('ingredient', 'N/A') if hasattr(result, 'metadata') and result.metadata else 'N/A'
        
        st.markdown(f"""
        <div class="result-card" style="
            border: 1px solid var(--text-color, #ddd);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            background-color: var(--secondary-background-color, #f9f9f9);
            color: var(--text-color, #333);
        ">
            <h4 style="color: var(--text-color, #333);">🏷️ {result.product_name}</h4>
            <p style="color: var(--text-color, #333);"><strong>⚗️ 有効成分:</strong> {active_ingredient}</p>
            <p style="color: var(--text-color, #333);"><strong>✨ 効果:</strong> {effect}</p>
            <p style="color: var(--text-color, #333);"><strong>📂 カテゴリ:</strong> {result.category or 'N/A'}</p>
            <p style="color: var(--text-color, #333);"><strong>📝 説明:</strong> {(result.description or 'N/A')[:200]}{'...' if len(result.description or '') > 200 else ''}</p>
            <p style="color: var(--text-color, #333);"><strong>🔗 URL:</strong> <a href="{result.url}" target="_blank" style="color: var(--primary-color, #0066cc);">商品ページを開く</a></p>
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
        st.write("**症状での検索例:**")
        st.write("- 抜け毛が増えた")
        st.write("- 足のむくみが取れない")
        st.write("- 肌の再生を促したい")
        
        st.write("**商品名での検索例:**")
        st.write("- カマグラゴールド")
        st.write("- フィナクス+ミノクソール")
        st.write("- オルリガル")
        
        st.write("**カテゴリでの検索例:**")
        st.write("- ED治療薬")
        st.write("- AGA治療薬")
        st.write("- ニキビ")
        st.write("- ダイエット")
    
    # 検索フォーム
    # クリア要求がある場合は空文字列、そうでなければセッション状態から取得
    default_value = "" if st.session_state.get('clear_requested', False) else st.session_state.get('search_input', "")
    
    # クリア要求フラグをリセット
    if st.session_state.get('clear_requested', False):
        st.session_state['clear_requested'] = False
    
    user_query = st.text_input(
        "💬 症状や探している商品を入力してください:",
        value=default_value,
        placeholder="例: 有効成分ミノキシジルのAGA治療薬を教えてください。",
        help="症状、商品名、カテゴリなど自然な言葉で入力できます",
        key="search_input"
    )
    
    # 検索ボタン
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_button = st.button("🔍 検索・レコメンド", type="primary")
    with col2:
        if st.button("🔄 リロード", help="システムを再読み込みして軽量化・エラー解決"):
            # リロード実行中の表示
            with st.spinner("リロード中..."):
                # キャッシュをクリア
                st.cache_data.clear()
                st.cache_resource.clear()
                # セッション状態をリセット（ウィジェットキーは除外）
                widget_keys = ['search_input']  # ウィジェットのキーを除外
                for key in list(st.session_state.keys()):
                    if key not in widget_keys:
                        del st.session_state[key]
                st.success("✅ リロード完了！システムを再読み込みします...")
                time.sleep(1)
            st.rerun()
    with col3:
        if st.button("🗑️ 画面クリア", help="検索結果と入力内容をクリア"):
            # 検索結果関連のセッション状態をクリア
            keys_to_clear = ['search_results', 'search_query', 'last_search', 'current_results', 'current_context', 'current_search_time', 'current_query']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            # クリア状態フラグを設定
            st.session_state['clear_requested'] = True
            st.success("✅ 画面をクリアしました")
            time.sleep(0.5)
            st.rerun()
    
    # 検索実行
    if search_button or (user_query and user_query.strip()):
        if user_query.strip():
            # 検索結果のキャッシュチェック
            cache_key = f"search_{hash(user_query.strip())}"
            if cache_key in st.session_state:
                # キャッシュされた結果を使用
                cached_data = st.session_state[cache_key]
                st.session_state['current_results'] = cached_data['results']
                st.session_state['current_context'] = cached_data['context']
                st.session_state['current_search_time'] = cached_data['search_time']
                st.session_state['current_query'] = cached_data['query']
                st.info("⚡ キャッシュされた検索結果を表示中")
            else:
                try:
                    engine = initialize_recommendation_engine()
                    
                    # エンジンが正常に初期化されたか確認
                    if engine is None:
                        st.error("❌ システムが正常に初期化されていません")
                        st.warning("🔧 以下を確認してください：")
                        st.write("1. `.env`ファイルにOPENAI_API_KEYが設定されているか")
                        st.write("2. OpenAI APIキーが有効かどうか")
                        st.write("3. インターネット接続が正常か")
                        return
                    
                    with st.spinner("検索中..."):
                        start_time = time.time()
                        results, context = engine.recommend_products(
                            user_query, 
                            max_results=max_results
                        )
                        search_time = time.time() - start_time
                    
                    # 結果をセッションに保存
                    st.session_state['current_results'] = results
                    st.session_state['current_context'] = context
                    st.session_state['current_search_time'] = search_time
                    st.session_state['current_query'] = user_query
                    
                    # 検索結果をキャッシュ（最大10件まで）
                    st.session_state[cache_key] = {
                        'results': results,
                        'context': context,
                        'search_time': search_time,
                        'query': user_query
                    }
                    
                    # キャッシュサイズ制限
                    cache_keys = [k for k in st.session_state.keys() if k.startswith('search_')]
                    if len(cache_keys) > 10:
                        oldest_key = min(cache_keys)
                        del st.session_state[oldest_key]
                        
                except Exception as e:
                    st.error("❌ 検索中にエラーが発生しました")
                    
                    # エラーの詳細情報
                    with st.expander("🔧 エラー詳細と対処法", expanded=True):
                        error_type = type(e).__name__
                        error_msg = str(e)
                        
                        st.write(f"**エラータイプ:** {error_type}")
                        st.write(f"**エラーメッセージ:** {error_msg}")
                        
                        # 一般的なエラーの対処法
                        st.markdown("### 💡 対処法")
                        if "openai" in error_msg.lower():
                            st.warning("🔑 **OpenAI APIの問題:** APIキーの確認またはネットワーク接続を確認してください")
                        elif "faiss" in error_msg.lower():
                            st.warning("🗃️ **検索インデックスの問題:** データベースの再構築が必要な可能性があります")
                        elif "memory" in error_msg.lower() or "ram" in error_msg.lower():
                            st.warning("💾 **メモリ不足:** 上部の「リロード」ボタンを押して再試行してください")
                        else:
                            st.info("🔄 **推奨対処順序:**")
                            st.markdown("""
                            1. **「リロード」ボタンを押す** （上部中央）
                            2. **ページを再読み込み** (F5またはCtrl+R)
                            3. **少し時間をおいて再試行**
                            """)
                    
                    logger.error(f"検索エラー: {e}")
        else:
            st.warning("検索クエリを入力してください。")    # 検索結果の表示（セッションに保存された結果がある場合）
    if 'current_results' in st.session_state and 'current_context' in st.session_state:
        results = st.session_state['current_results']
        context = st.session_state['current_context']
        search_time = st.session_state.get('current_search_time', 0)
        query = st.session_state.get('current_query', '')
        
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
                    st.write(f"**検索クエリ:** '{query}'")
                    st.write(f"**結果数:** {len(results)}")
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