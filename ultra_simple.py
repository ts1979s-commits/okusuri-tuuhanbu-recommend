import streamlit as st
import pandas as pd

st.title("💊 お薬通販部")

try:
    df = pd.read_csv("data/product_recommend.csv", encoding='utf-8-sig')
    st.success(f"✅ {len(df)}件のデータ")
    
    query = st.text_input("検索:")
    
    if query:
        mask = df['商品名'].str.contains(query, case=False, na=False)
        results = df[mask]
        
        if not results.empty:
            for _, row in results.head(5).iterrows():
                st.write(f"**{row['商品名']}**")
                st.write(f"カテゴリ: {row['カテゴリ']}")
                st.write("---")
        else:
            st.write("該当商品なし")
            
except Exception as e:
    st.error(f"エラー: {e}")