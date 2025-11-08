import streamlit as st
import pandas as pd
import os

# ページ設定
st.set_page_config(page_title="お薬通販部", page_icon="💊")

st.title("💊 お薬通販部 商品レコメンド")

# データ読み込み
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data/product_recommend.csv", encoding='utf-8-sig')
        return df.to_dict('records')
    except:
        return []

products = load_data()

if not products:
    st.error("データが読み込まれていません")
    st.stop()

st.success(f"✅ {len(products)}件の商品データ")

# 検索
query = st.text_input("商品を検索:", placeholder="例: サプリメント")

if query:
    results = []
    for product in products:
        score = 0
        product_name = str(product.get('商品名', ''))
        category = str(product.get('カテゴリ', ''))
        
        if query.lower() in product_name.lower():
            score += 3
        if query.lower() in category.lower():
            score += 2
            
        if score > 0:
            results.append((product, score))
    
    results.sort(key=lambda x: x[1], reverse=True)
    
    if results:
        st.write(f"🎯 {len(results)}件見つかりました:")
        
        for product, score in results[:5]:
            st.write(f"**{product.get('商品名', '')}**")
            st.write(f"カテゴリ: {product.get('カテゴリ', '')}")
            st.write("---")
    else:
        st.write("該当商品なし")

# サイドバー検索例
with st.sidebar:
    st.header("検索例")
    if st.button("サプリメント"):
        st.session_state.search = "サプリメント"
        st.rerun()
    if st.button("ED治療薬"):
        st.session_state.search = "ED治療薬"
        st.rerun()
    if st.button("トリファラ"):
        st.session_state.search = "トリファラ"
        st.rerun()

if 'search' in st.session_state:
    st.text_input("商品を検索:", value=st.session_state.search, key='search_box')
    del st.session_state.search