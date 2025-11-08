# -*- coding: utf-8 -*-
"""
Streamlit Web UI - お薬通販部商品レコメンドLLMアプリ
ユーザーフレンドリーなWeb インターフェース
"""
import streamlit as st
import sys
import os
import pandas as pd
from typing import List, Dict, Any
import logging
import time

# 安全なインポート
try:
    # パスを追加
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, current_dir)
    sys.path.insert(0, parent_dir)
    
    # FAISSRAGSystemのインポート
    from src.faiss_rag_system import FAISSRAGSystem
    FAISS_AVAILABLE = True
except ImportError as e:
    st.warning(f"⚠️ AI機能の読み込みに失敗: {e}")
    FAISS_AVAILABLE = False

# 設定の読み込み（オプション）
try:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY')
except:
    OPENAI_API_KEY = None

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

@st.cache_data
def load_basic_data():
    """CSVデータを読み込む"""
    try:
        df = pd.read_csv("data/product_recommend.csv", encoding='utf-8-sig')
        return df.to_dict('records')
    except Exception as e:
        st.error(f"データファイルの読み込みに失敗: {e}")
        return []

def basic_search(products, query):
    """基本検索機能"""
    results = []
    for product in products:
        score = 0
        product_name = str(product.get('商品名', ''))
        category = str(product.get('カテゴリ名', ''))
        
        if query.lower() in product_name.lower():
            score += 3
        if query.lower() in category.lower():
            score += 2
            
        if score > 0:
            results.append((product, score))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def display_basic_results(results):
    """基本検索結果を表示"""
    if results:
        st.write(f"🎯 {len(results)}件見つかりました:")
        
        for product, score in results[:5]:
            with st.container():
                st.markdown(f"**{product.get('商品名', '')}**")
                st.write(f"📂 カテゴリ: {product.get('カテゴリ名', '')}")
                if product.get('効果'):
                    st.write(f"💊 効果: {product.get('効果', '')}")
                if product.get('有効成分'):
                    st.write(f"🧪 有効成分: {product.get('有効成分', '')}")
                st.divider()
    else:
        st.write("該当商品がありません")

def display_ai_results(results, search_time):
    """AI検索結果を表示"""
    if results:
        st.markdown("---")
        st.subheader("📋 検索結果")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("結果数", len(results))
        with col2:
            st.metric("検索時間", f"{search_time:.2f}秒")
        
        st.markdown("### 🎯 おすすめ商品")
        for i, result in enumerate(results, 1):
            with st.container():
                st.markdown(f"**{i}. {result.product_name}**")
                st.write(f"📂 **カテゴリ:** {result.category}")
                if hasattr(result, 'metadata') and result.metadata:
                    if 'effect' in result.metadata:
                        st.write(f"💊 **効果:** {result.metadata['effect']}")
                    if 'ingredient' in result.metadata:
                        st.write(f"🧪 **有効成分:** {result.metadata['ingredient']}")
                st.write(f"📝 **説明:** {(result.description or 'N/A')[:200]}{'...' if len(result.description or '') > 200 else ''}")
                if result.url:
                    st.write(f"🔗 [商品ページを開く]({result.url})")
                st.write(f"**類似度:** {result.similarity_score:.3f}")
                st.divider()
    else:
        st.warning("該当する商品が見つかりませんでした。")

def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.title("💊 お薬通販部 商品レコメンド AI")
    st.markdown("---")

    # データ読み込み
    products = load_basic_data()
    if not products:
        st.error("商品データが利用できません。")
        return

    st.success(f"✅ {len(products)}件の商品データが利用可能")

    # AI機能の初期化
    rag_system = None
    ai_mode = False
    
    if FAISS_AVAILABLE and OPENAI_API_KEY:
        try:
            with st.spinner("AI システム初期化中..."):
                @st.cache_resource
                def init_system():
                    try:
                        return FAISSRAGSystem()
                    except Exception as init_error:
                        logger.error(f"FAISSRAGSystem初期化エラー: {init_error}")
                        raise init_error
                
                rag_system = init_system()
                ai_mode = True
            
            st.success("✅ AI機能が利用可能です")
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"AI機能初期化エラー: {error_type}: {error_msg}")
            
            # ProxyConnectionErrorの特別処理
            if error_type == "ProxyConnectionError":
                st.warning("🔧 **プロキシ設定のため AI機能は利用できません**")
                st.info("Streamlit Cloud環境のプロキシ設定により、OpenAI APIに接続できませんでした。基本検索機能をご利用ください。")
            # 一般的なプロキシエラーの処理
            elif "proxies" in error_msg.lower() or "プロキシ" in error_msg or "proxy" in error_msg.lower():
                st.warning("🔧 **プロキシ設定エラー**: OpenAI接続でプロキシ設定に問題があります")
                st.info("💡 **解決方法**: ")
                st.markdown("""
                - 現在プロキシ設定の問題により AI機能が利用できません
                - 基本検索機能は正常にご利用いただけます
                - 管理者によりプロキシ設定を調整中です
                """)
            elif "got an unexpected keyword argument 'proxies'" in error_msg:
                st.warning("🔧 **OpenAIライブラリ設定エラー**: プロキシ引数の競合が発生しています")
                st.info("💡 **解決方法**: ライブラリバージョンの問題のため、基本検索をご利用ください")
            elif "api_key" in error_msg.lower() or "apikey" in error_msg.lower():
                st.warning("🔑 **APIキー設定エラー**: OpenAI APIキーの設定に問題があります")
                st.info("💡 **解決方法**: OPENAI_API_KEYを正しく設定してください")
            elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                st.warning("🌐 **接続エラー**: OpenAIサービスへの接続に失敗しました")
                st.info("💡 **解決方法**: インターネット接続を確認してください")
            elif "依存関係" in error_msg or "dependencies" in error_msg.lower():
                st.warning("📦 **依存関係エラー**: 必要なライブラリが不足しています")
                st.info("💡 **解決方法**: requirements.txtの依存関係をインストールしてください")
            elif "timeout" in error_msg.lower():
                st.warning("⏰ **タイムアウトエラー**: OpenAI APIの応答が遅延しています")
                st.info("💡 **解決方法**: しばらく時間をおいてから再試行してください")
            else:
                st.warning(f"⚠️ **AI機能初期化エラー**: {error_type}")
                with st.expander("詳細エラー情報"):
                    st.code(error_msg)
                    if st.secrets.get("debug_mode", False):
                        import traceback
                        st.code(traceback.format_exc())
            
            st.success("✅ 基本検索機能は正常に利用できます")
            logger.warning(f"AI機能初期化失敗、基本モードで継続: {e}")
    else:
        if not OPENAI_API_KEY:
            st.info("ℹ️ OpenAI APIキーが設定されていません。基本検索モードで動作します。")
        else:
            st.info("ℹ️ AI機能が利用できません。基本検索モードで動作します。")

    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        max_results = st.slider("最大結果数", 1, 10, 5)
        
        st.header("💡 検索例")
        st.write("**症状での検索例:**")
        st.write("- ED治療薬")
        st.write("- AGA治療薬") 
        st.write("- 便秘改善")

    # 検索インターフェース
    search_mode = "AI検索" if ai_mode else "基本検索"
    st.header(f"🔍 商品検索 ({search_mode})")
    
    # 検索フォーム
    user_query = st.text_input(
        "💬 症状や探している商品を入力してください:",
        placeholder="例: ED治療薬、AGA治療薬",
        help="症状、商品名、カテゴリなど自然な言葉で入力できます"
    )
    
    # 検索実行
    if st.button("🔍 検索", type="primary") and user_query:
        if ai_mode and rag_system:
            # AI検索
            try:
                with st.spinner("AI検索中..."):
                    start_time = time.time()
                    results = rag_system.search_products(user_query, top_k=max_results)
                    search_time = time.time() - start_time
                
                display_ai_results(results, search_time)
                
            except Exception as e:
                st.error(f"❌ AI検索中にエラーが発生しました: {e}")
                st.info("基本検索にフォールバックします")
                
                # フォールバック: 基本検索
                results = basic_search(products, user_query)
                display_basic_results(results)
        else:
            # 基本検索
            results = basic_search(products, user_query)
            display_basic_results(results)

    # フッター
    st.markdown("---")
    st.markdown("💊 お薬通販部 商品レコメンド AI - Powered by OpenAI + FAISS")

if __name__ == "__main__":
    main()