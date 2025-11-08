"""
お薬通販部 商品レコメンド AI - 最終安定版
"""
import streamlit as st
import pandas as pd
import os
from typing import List, Dict, Any

# ページ設定（一度だけ実行）
if 'page_config_set' not in st.session_state:
    st.set_page_config(
        page_title="お薬通販部レコメンド",
        page_icon="💊",
        layout="wide"
    )
    st.session_state.page_config_set = True

class SimpleSearchEngine:
    """シンプルな検索エンジン"""
    
    def __init__(self):
        self.products = []
        self.load_data()
    
    def load_data(self):
        """CSVデータを読み込み"""
        try:
            csv_file = "data/product_recommend.csv"
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                
                for _, row in df.iterrows():
                    product = {
                        'name': str(row.get('商品名', '')),
                        'category': str(row.get('カテゴリ', '')),
                        'subcategory': str(row.get('サブカテゴリ', '')),
                        'effect': str(row.get('効果', '')),
                        'ingredient': str(row.get('有効成分', '')),
                        'url': str(row.get('URL', ''))
                    }
                    self.products.append(product)
                
                st.sidebar.success(f"✅ {len(self.products)}件の商品を読み込み")
            else:
                st.sidebar.error("❌ CSVファイルが見つかりません")
                
        except Exception as e:
            st.sidebar.error(f"データ読み込みエラー: {e}")
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """検索実行"""
        if not query.strip() or not self.products:
            return []
        
        query_lower = query.lower()
        results = []
        
        for product in self.products:
            score = 0
            
            # 商品名マッチング
            if query_lower in product['name'].lower():
                score += 3
            
            # カテゴリマッチング
            if query_lower in product['category'].lower():
                score += 2
            
            # サブカテゴリマッチング
            if query_lower in product['subcategory'].lower():
                score += 2
            
            # 効果マッチング
            if query_lower in product['effect'].lower():
                score += 1
            
            # 成分マッチング
            if query_lower in product['ingredient'].lower():
                score += 1
            
            # サプリメント特別処理
            if 'サプリ' in query_lower:
                if 'サプリ' in product['category'].lower() or 'サプリ' in product['subcategory'].lower():
                    score += 2
                if product['name'] in ['トリファラ', 'プエラリアミリフィカタブレット']:
                    score += 3
            
            if score > 0:
                product['score'] = score
                results.append(product)
        
        # スコア順でソート
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

def main():
    """メイン関数"""
    
    # タイトル
    st.title("💊 お薬通販部 商品レコメンド AI")
    
    # 検索エンジン初期化
    if 'search_engine' not in st.session_state:
        with st.spinner("システム初期化中..."):
            st.session_state.search_engine = SimpleSearchEngine()
    
    search_engine = st.session_state.search_engine
    
    if not search_engine.products:
        st.error("❌ 商品データが読み込まれていません")
        st.stop()
    
    # サイドバー
    with st.sidebar:
        st.header("🔍 検索メニュー")
        
        if st.button("🔄 データ再読み込み"):
            del st.session_state.search_engine
            st.rerun()
        
        st.write("---")
        st.write("**よく検索される商品:**")
        
        if st.button("サプリメント"):
            st.session_state.search_query = "サプリメント"
        if st.button("ED治療薬"):
            st.session_state.search_query = "ED治療薬"
        if st.button("AGA治療薬"):
            st.session_state.search_query = "AGA治療薬"
        if st.button("美容・スキンケア"):
            st.session_state.search_query = "美容・スキンケア"
        if st.button("ダイエット"):
            st.session_state.search_query = "ダイエット"
        
        st.write("**個別商品:**")
        if st.button("カマグラゴールド"):
            st.session_state.search_query = "カマグラゴールド"
        if st.button("トリファラ"):
            st.session_state.search_query = "トリファラ"
        if st.button("プエラリア"):
            st.session_state.search_query = "プエラリア"
    
    # メイン検索エリア
    st.subheader("🔍 商品検索")
    
    # 検索フォーム
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "検索キーワードを入力:",
            value=st.session_state.get('search_query', ''),
            placeholder="例：サプリメント、カマグラゴールド",
            key="search_input"
        )
    
    with col2:
        st.write("")  # スペーサー
        search_clicked = st.button("🔍 検索", type="primary")
    
    # 検索実行
    if (search_clicked or query != st.session_state.get('last_query', '')) and query.strip():
        st.session_state.last_query = query
        
        with st.spinner(f"「{query}」を検索中..."):
            results = search_engine.search(query, limit=8)
        
        if results:
            st.success(f"🎯 {len(results)}件の商品が見つかりました")
            
            # 結果表示
            for i, product in enumerate(results, 1):
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.write(f"### {i}. {product['name']}")
                        st.write(f"📂 **カテゴリ:** {product['category']}")
                        
                        if product['subcategory'] != 'nan' and product['subcategory']:
                            st.write(f"📋 **サブカテゴリ:** {product['subcategory']}")
                        
                        if product['effect'] != 'nan' and product['effect']:
                            st.write(f"✨ **効果:** {product['effect']}")
                        
                        if product['ingredient'] != 'nan' and product['ingredient']:
                            st.write(f"⚗️ **有効成分:** {product['ingredient']}")
                        
                        if product.get('url') and product['url'] != 'nan':
                            st.write(f"🔗 [商品ページを開く]({product['url']})")
                    
                    with col2:
                        score = product['score']
                        if score >= 3:
                            color = "#4CAF50"
                            level = "高"
                        elif score >= 2:
                            color = "#FF9800"
                            level = "中"
                        else:
                            color = "#F44336"
                            level = "低"
                        
                        st.markdown(f"""
                        <div style="
                            background-color: {color}; 
                            color: white; 
                            padding: 1rem; 
                            border-radius: 10px; 
                            text-align: center;
                        ">
                            関連度<br><strong>{level}</strong><br>({score})
                        </div>
                        """, unsafe_allow_html=True)
                
                st.divider()
        else:
            st.warning("🤔 該当する商品が見つかりませんでした")
            st.info("💡 別のキーワードで検索してみてください")
            
            # 検索ヒント
            with st.expander("💡 検索のヒント"):
                st.write("**効果的な検索方法:**")
                st.write("- 商品名: カマグラ、トリファラ、スペマンなど")
                st.write("- カテゴリ: サプリメント、ED治療薬、AGA治療薬など")
                st.write("- 症状: むくみ、便秘、抜け毛など")
                st.write("- 成分名: シルデナフィル、ミノキシジルなど")
    
    # 統計情報
    if st.checkbox("📊 データベース統計"):
        categories = {}
        for product in search_engine.products:
            cat = product['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        st.write("**カテゴリ別商品数:**")
        for cat, count in sorted(categories.items()):
            if cat != 'nan':
                st.write(f"- {cat}: {count}件")
    
    # フッター
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 0.9rem;'>
            💊 お薬通販部 商品レコメンド AI<br>
            シンプル・高速検索システム
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()