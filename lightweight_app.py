"""
超軽量版 Streamlit アプリ - sentence-transformers不要
"""
import streamlit as st
import os
import sys
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import traceback

# ページ設定
st.set_page_config(
    page_title="お薬通販部レコメンド",
    page_icon="💊"
)

@dataclass
class SimpleSearchResult:
    """軽量な検索結果クラス"""
    product_name: str
    category: str
    effect: str
    ingredient: str
    url: str = ""
    score: float = 0.0

class LightweightSearchEngine:
    """軽量検索エンジン（sentence-transformers不要）"""
    
    def __init__(self):
        self.products = []
        self._load_csv_data()
    
    def _load_csv_data(self):
        """CSVデータを読み込み"""
        try:
            csv_path = "data/product_recommend.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
                st.success(f"✅ CSVデータ読み込み: {len(df)}件")
                
                for _, row in df.iterrows():
                    product = {
                        'name': str(row.get('商品名', '')),
                        'category': str(row.get('カテゴリ', '')),
                        'subcategory': str(row.get('サブカテゴリ', '')),
                        'effect': str(row.get('効果', '')),
                        'ingredient': str(row.get('有効成分', '')),
                        'description': str(row.get('説明', '')),
                        'url': str(row.get('URL', ''))
                    }
                    self.products.append(product)
                    
                st.info(f"商品データ: {len(self.products)}件読み込み完了")
            else:
                st.error(f"❌ CSVファイルが見つかりません: {csv_path}")
        except Exception as e:
            st.error(f"CSVデータ読み込みエラー: {e}")
    
    def search(self, query: str, top_k: int = 5) -> List[SimpleSearchResult]:
        """シンプルなキーワード検索"""
        if not self.products:
            return []
        
        query_lower = query.lower()
        results = []
        
        for product in self.products:
            score = 0.0
            
            # 商品名での完全一致（最高スコア）
            if query_lower in product['name'].lower():
                score += 2.0
            
            # カテゴリでの一致
            if query_lower in product['category'].lower():
                score += 1.5
            
            # サブカテゴリでの一致
            if query_lower in product['subcategory'].lower():
                score += 1.3
            
            # 効果での一致
            if query_lower in product['effect'].lower():
                score += 1.0
            
            # 有効成分での一致
            if query_lower in product['ingredient'].lower():
                score += 0.8
            
            # 説明での一致
            if query_lower in product['description'].lower():
                score += 0.5
            
            # キーワード別の特別処理
            if 'サプリ' in query_lower:
                if any(word in product['category'].lower() + product['subcategory'].lower() 
                       for word in ['サプリ', '便秘薬', 'バストアップ']):
                    score += 1.0
                # 特定商品のボーナス
                if product['name'] in ['トリファラ', 'プエラリアミリフィカタブレット']:
                    score += 1.5
            
            if score > 0:
                result = SimpleSearchResult(
                    product_name=product['name'],
                    category=product['category'],
                    effect=product['effect'],
                    ingredient=product['ingredient'],
                    url=product['url'],
                    score=score
                )
                results.append(result)
        
        # スコア順でソート
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

def main():
    st.title("💊 お薬通販部 商品レコメンド AI")
    st.write("軽量版 - 高速キーワード検索")
    
    # API キー確認（表示のみ）
    try:
        api_key = None
        if hasattr(st, 'secrets'):
            try:
                if 'secrets' in st.secrets:
                    api_key = st.secrets['secrets'].get('OPENAI_API_KEY')
                if not api_key:
                    api_key = st.secrets.get('OPENAI_API_KEY')
            except:
                pass
        
        if api_key and api_key.startswith('sk-'):
            st.success("✅ APIキー設定確認済み")
        else:
            st.info("ℹ️ APIキー未設定（軽量版では不要）")
    except:
        st.info("ℹ️ 軽量版モード（APIキー不要）")
    
    # 検索エンジン初期化
    with st.spinner("検索エンジン初期化中..."):
        try:
            search_engine = LightweightSearchEngine()
            if len(search_engine.products) > 0:
                st.success(f"✅ 検索エンジン準備完了: {len(search_engine.products)}件の商品")
            else:
                st.error("❌ 商品データが読み込まれていません")
                return
        except Exception as e:
            st.error(f"検索エンジン初期化エラー: {e}")
            st.text(traceback.format_exc())
            return
    
    # 検索インターフェース
    st.write("---")
    st.subheader("🔍 商品検索")
    
    # よく使われる検索例
    st.write("**よく検索される商品:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("サプリメント"):
            st.session_state['search_query'] = "サプリメント"
    with col2:
        if st.button("ED治療薬"):
            st.session_state['search_query'] = "ED治療薬"
    with col3:
        if st.button("AGA治療薬"):
            st.session_state['search_query'] = "AGA治療薬"
    with col4:
        if st.button("美容"):
            st.session_state['search_query'] = "美容"
    
    # 個別商品検索
    st.write("**個別商品:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("カマグラゴールド"):
            st.session_state['search_query'] = "カマグラゴールド"
    with col2:
        if st.button("トリファラ"):
            st.session_state['search_query'] = "トリファラ"
    with col3:
        if st.button("プエラリア"):
            st.session_state['search_query'] = "プエラリア"
    with col4:
        if st.button("スペマン"):
            st.session_state['search_query'] = "スペマン"
    
    # 検索入力
    query = st.text_input(
        "検索キーワード:",
        value=st.session_state.get('search_query', ''),
        placeholder="商品名や症状を入力してください",
        key='search_input'
    )
    
    # 検索実行
    if st.button("🔍 検索", type="primary") and query.strip():
        with st.spinner(f"「{query}」を検索中..."):
            try:
                results = search_engine.search(query, top_k=8)
                
                if results:
                    st.success(f"🎯 {len(results)}件の商品が見つかりました")
                    
                    for i, result in enumerate(results, 1):
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            
                            with col1:
                                st.write(f"**{i}. {result.product_name}**")
                                st.write(f"📂 カテゴリ: {result.category}")
                                
                                if result.effect:
                                    st.write(f"✨ 効果: {result.effect}")
                                
                                if result.ingredient:
                                    st.write(f"⚗️ 有効成分: {result.ingredient}")
                                
                                if result.url:
                                    st.write(f"🔗 [商品ページを開く]({result.url})")
                            
                            with col2:
                                score = result.score
                                color = "#4CAF50" if score >= 2.0 else "#FF9800" if score >= 1.0 else "#F44336"
                                st.markdown(f"""
                                <div style="
                                    background-color: {color}; 
                                    color: white; 
                                    padding: 0.5rem; 
                                    border-radius: 10px; 
                                    text-align: center;
                                ">
                                    スコア<br><strong>{score:.1f}</strong>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        st.divider()
                else:
                    st.warning("🤔 該当する商品が見つかりませんでした")
                    st.info("💡 別のキーワードで検索してみてください")
                    
                    # 検索のヒント
                    st.write("**検索のコツ:**")
                    st.write("- 商品名で検索: カマグラ、トリファラ、スペマンなど")
                    st.write("- カテゴリで検索: サプリメント、ED治療薬、AGA治療薬など")
                    st.write("- 症状で検索: むくみ、便秘、抜け毛など")
            
            except Exception as e:
                st.error(f"❌ 検索エラー: {e}")
                st.text(traceback.format_exc())
    
    # 統計情報
    if st.checkbox("📊 システム統計"):
        with st.expander("データベース統計", expanded=False):
            if hasattr(search_engine, 'products') and search_engine.products:
                categories = {}
                for product in search_engine.products:
                    cat = product['category']
                    categories[cat] = categories.get(cat, 0) + 1
                
                st.write("**カテゴリ別商品数:**")
                for cat, count in sorted(categories.items()):
                    st.write(f"- {cat}: {count}件")
            else:
                st.write("データが読み込まれていません")
    
    # フッター
    st.write("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 0.9rem;'>"
        "💊 お薬通販部 商品レコメンド AI - 軽量版<br>"
        "高速キーワード検索エンジン"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()